"""Time of day and the day boundary come from TrustedClock; usage grows only by time.monotonic() deltas capped at
MAX_STEP per tick, so changing the system clock cannot add quota and sleep is not counted.
A session is enforced only when its SID is in a signed policy's accounts; other accounts are left alone.
Time counts while the session is logged on, not locked, and the Tray UI reports less than IDLE_LIMIT idle.
Without a recent Tray UI heartbeat idle time is unknown, so the time counts (fail closed).
Running out during use starts GRACE_SECONDS of grace. If time is already out at logon, unlock, service start
or a child switch, there is no grace and the lock is immediate. While locked and the session is still unlocked, a new
lock order goes out every RELOCK_SECONDS in case the previous one was lost.
The Tray UI performs the actual lock because LockWorkStation only works inside the user's session.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime
from types import ModuleType

from service.core.agent import ModuleContext
from service.core.alerts import AlertBoard
from service.core.bus import SESSION, TRAY_HEARTBEAT, Bus, SessionEvent, SessionInfo, TrayPing
from service.core.device_session import DeviceSession
from service.core.event_queue import EventQueue
from service.core.events import MAX_DURATION_SEC, EventInvalid, format_ts
from service.core.policy_store import EffectivePolicy, PolicyStore
from service.core.screen_state import STATE_GRACE, STATE_LOCKED, STATE_NONE, STATE_OK, ScreenState
from service.core.trusted_clock import TrustedClock
from service.modules.screentime.counters import Activity, ChildCounter, CounterSet
from service.modules.screentime.schedule import day_key, quota_minutes, seconds_until_closed

log = logging.getLogger("ogk.screentime")

TICK_SECONDS = 1.0
MAX_STEP = 2.0
IDLE_LIMIT = 300.0
TRAY_STALE_SECONDS = 15.0
GRACE_SECONDS = 60.0
RELOCK_SECONDS = 5.0
SAVE_SECONDS = 30.0
WARNINGS = (600, 300, 60)
REASON_QUOTA = "quota"
REASON_SCHEDULE = "schedule"
ALERT_CLOCK_TAMPERED = "clock_tampered"


class ScreenTimeModule:
    def __init__(
        self,
        store: PolicyStore,
        clock: TrustedClock,
        counters: CounterSet,
        screen: ScreenState,
        alerts: AlertBoard,
        bus: Bus,
        platform: ModuleType,
        queue: EventQueue | None = None,
        session: DeviceSession | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        interval: float = TICK_SECONDS,
    ) -> None:
        self._store = store
        self._clock = clock
        self._counters = counters
        self._screen = screen
        self._alerts = alerts
        self._platform = platform
        self._queue = queue
        self._device = session
        self._monotonic = monotonic
        self._interval = interval
        self._user: SessionInfo | None = None
        self._screen_locked = False
        self._fresh = True
        self._child: int | None = None
        self._last_tick: float | None = None
        self._last_ping: float | None = None
        self._idle: float | None = None
        self._grace_until: float | None = None
        self._last_lock: float | None = None
        self._last_save: float | None = None
        self._save_now = False
        self._prev_remaining: int | None = None
        self._warned: set[int] = set()
        bus.subscribe(SESSION, self._on_session)
        bus.subscribe(TRAY_HEARTBEAT, self._on_ping)

    def _on_session(self, event: SessionEvent) -> None:
        if event.kind in ("logon", "unlock"):
            self._user = self._platform.current_session()
            self._screen_locked = False
            self._fresh = True
        elif event.kind == "lock":
            self._screen_locked = True
            self._save_now = True
        elif event.kind == "logoff":
            self._user = None
            self._screen_locked = False
            self._save_now = True

    def _on_ping(self, ping: TrayPing) -> None:
        self._last_ping = self._monotonic()
        self._idle = ping.idle_seconds

    def _is_idle(self, now: float) -> bool:
        if self._last_ping is None or now - self._last_ping > TRAY_STALE_SECONDS:
            return False
        return self._idle is not None and self._idle >= IDLE_LIMIT

    async def start(self) -> None:
        await asyncio.to_thread(self._clock.load)
        await asyncio.to_thread(self._counters.open_day, day_key(self._clock.local_now()))
        self._user = self._platform.current_session()
        self._last_tick = self._last_save = self._monotonic()

    async def run(self) -> None:
        await self.start()
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("screen time tick failed")
            await asyncio.sleep(self._interval)

    def _check_clock(self) -> None:
        direction = self._clock.check()
        if direction is None:
            self._alerts.clear(ALERT_CLOCK_TAMPERED)
        else:
            self._alerts.raise_(ALERT_CLOCK_TAMPERED, direction, self._clock.now())

    async def _roll_day(self, day: str) -> None:
        await asyncio.to_thread(self._counters.save, self._clock.now())
        await asyncio.to_thread(self._counters.open_day, day)
        self._warned.clear()
        self._prev_remaining = None
        log.info("new day %s, usage counters reset", day)

    async def _persist(self, now: float) -> None:
        if not self._save_now and self._last_save is not None and now - self._last_save < SAVE_SECONDS:
            return
        await asyncio.to_thread(self._counters.save, self._clock.now())
        await asyncio.to_thread(self._clock.save)
        self._last_save = now
        self._save_now = False

    def _current_child(self) -> int | None:
        if self._user is None:
            return None
        return self._store.child_for_sid(self._user.sid)

    async def tick(self) -> None:
        now = self._monotonic()
        step = 0.0 if self._last_tick is None else min(max(0.0, now - self._last_tick), MAX_STEP)
        self._last_tick = now
        self._check_clock()
        local = self._clock.local_now()
        if day_key(local) != self._counters.day:
            await self._roll_day(day_key(local))

        child = self._current_child()
        if child != self._child:
            self._child = child
            self._fresh = True
            self._grace_until = None
            self._prev_remaining = None
            if self._screen.state == STATE_LOCKED or self._screen.state == STATE_GRACE:
                self._screen.state = STATE_NONE
        policy = None if child is None else self._store.rules_for(child)
        if child is None or policy is None:
            self._reset_screen()
        else:
            active = not self._screen_locked and not self._is_idle(now) and self._screen.state != STATE_LOCKED
            self._counters.record(Activity(child, active), step)
            await self._evaluate(child, policy, local, now, active)
        self._screen.used_today = {cid: int(seconds) for cid, seconds in self._counters.by_child().items()}
        await self._persist(now)

    def _reset_screen(self) -> None:
        self._screen.child_id = None
        self._screen.state = STATE_NONE
        self._screen.counting = False
        self._screen.remaining_seconds = None
        self._screen.quota_seconds = None
        self._screen.grace_seconds = None
        self._screen.lock_reason = None
        self._screen.warning = None

    async def _evaluate(self, child: int, policy: EffectivePolicy, local: datetime, now: float, active: bool) -> None:
        rules = policy.rules
        used = self._counters.used(child)
        quota = quota_minutes(rules, local.date()) * 60
        quota_left = max(0, int(quota - used))
        schedule_left = seconds_until_closed(rules["weekly_schedule"], local)
        remaining = min(quota_left, schedule_left)
        reason = REASON_SCHEDULE if schedule_left <= quota_left else REASON_QUOTA
        screen = self._screen
        screen.child_id = child
        screen.counting = active
        screen.used_seconds = int(used)
        screen.quota_seconds = quota
        screen.remaining_seconds = remaining
        screen.set_by = policy.set_by
        fresh, self._fresh = self._fresh, False

        if remaining > 0:
            if screen.state in (STATE_LOCKED, STATE_GRACE):
                log.info("child %s has time again (%ss), unlocked", child, remaining)
            screen.state = STATE_OK
            screen.lock_reason = None
            screen.grace_seconds = None
            self._grace_until = None
            if not fresh:
                await self._warn(child, policy, used, remaining)
            self._prev_remaining = remaining
            return

        self._prev_remaining = 0
        if screen.state == STATE_LOCKED:
            if fresh:
                await self._lock(child, policy, used, screen.lock_reason or reason, now, event=True)
            elif not self._screen_locked and now - (self._last_lock or 0.0) >= RELOCK_SECONDS:
                await self._lock(child, policy, used, screen.lock_reason or reason, now, event=False)
            return
        if screen.state == STATE_GRACE and self._grace_until is not None:
            screen.grace_seconds = max(0, int(self._grace_until - now + 0.999))
            if now >= self._grace_until:
                await self._lock(child, policy, used, screen.lock_reason or reason, now, event=True)
            return
        if fresh:
            await self._lock(child, policy, used, reason, now, event=True)
            return
        screen.state = STATE_GRACE
        screen.lock_reason = reason
        self._grace_until = now + GRACE_SECONDS
        screen.grace_seconds = int(GRACE_SECONDS)
        log.info("child %s is out of time (%s), %ds grace", child, reason, GRACE_SECONDS)

    async def _warn(self, child: int, policy: EffectivePolicy, used: float, remaining: int) -> None:
        self._warned = {t for t in self._warned if t >= remaining}
        previous = self._prev_remaining
        if previous is None:
            return
        crossed = [t for t in WARNINGS if previous > t >= remaining and t not in self._warned]
        if not crossed:
            return
        self._warned.update(crossed)
        threshold = min(crossed)
        self._screen.warning = threshold // 60
        self._screen.warning_seq += 1
        log.info("child %s has %ss left, warning %d min", child, remaining, threshold // 60)
        await self._emit(child, policy, "quota_warning", str(threshold // 60), used)

    async def _lock(
        self, child: int, policy: EffectivePolicy, used: float, reason: str, now: float, *, event: bool
    ) -> None:
        screen = self._screen
        screen.state = STATE_LOCKED
        screen.lock_reason = reason
        screen.grace_seconds = None
        screen.lock_seq += 1
        self._grace_until = None
        self._last_lock = now
        self._save_now = True
        if event:
            log.info("locking child %s: %s", child, reason)
            await self._emit(child, policy, "locked", reason, used)

    async def _emit(self, child: int, policy: EffectivePolicy, kind: str, subject: str, used: float) -> None:
        device_id = None if self._device is None else self._device.device_id
        if self._queue is None or device_id is None:
            return
        event = {
            "ts": format_ts(self._clock.now()),
            "device_id": device_id,
            "child_id": child,
            "type": kind,
            "subject": subject,
            "duration_sec": min(int(used), MAX_DURATION_SEC),
            "policy_id": policy.version,
        }
        try:
            await self._queue.enqueue([event])
        except EventInvalid as exc:
            log.error("dropped %s event: invalid %s", kind, exc.field)


def create(context: ModuleContext) -> ScreenTimeModule:
    return ScreenTimeModule(
        context.policy_store,
        context.clock,
        CounterSet(context.db, [ChildCounter()]),
        context.screen,
        context.alerts,
        context.bus,
        context.platform,
        context.event_queue,
        context.session,
    )
