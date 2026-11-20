"""Only processes that appeared since the last scan are checked; a new child, a new policy version or enforcement
coming back clears that memory so already running apps are checked against the new rules.
Nothing is killed while enforcement is disabled: the Tray UI is what explains a block, and a block it cannot
explain would be silent.
A name match blocks at once; a hash match waits for the SHA-256, which runs in a worker thread. When the
policy has an allow rule with a hash, a name match also waits, since that allow may cover the same file.
When the policy has hash rules and a known exe cannot be hashed even through platform.read_chunks (file
renamed or deleted after launch, unreadable), the app is blocked: a seen process is never checked again, so
letting it through would turn any unreadable copy into a way around every hash rule.
App time follows the foreground exe that the Tray UI reports with each heartbeat; background apps never get
time. The interval ends on lock, logoff, a child switch, idle, or a Tray UI that went quiet, and is cut into
MAX_DURATION_SEC pieces so each app_stop stays within the event schema.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from types import ModuleType

from service.core.agent import ModuleContext
from service.core.app_state import AppState
from service.core.bus import SESSION, TRAY_HEARTBEAT, Bus, SessionEvent, SessionInfo, TrayPing
from service.core.device_session import DeviceSession
from service.core.enforcement import Enforcement
from service.core.event_queue import EventQueue
from service.core.events import MAX_DURATION_SEC, EventInvalid, format_ts
from service.core.policy_store import EffectivePolicy, PolicyStore
from service.core.process_info import ProcInfo
from service.core.screen_state import STATE_LOCKED, ScreenState
from service.core.trusted_clock import TrustedClock
from service.modules.appcontrol.hashing import HashCache
from service.modules.appcontrol.rules import BLOCK, blocked_by_name, decide, has_hash_rules, is_protected

log = logging.getLogger("ogk.appcontrol")

TICK_SECONDS = 1.0
IDLE_LIMIT = 300.0
TRAY_STALE_SECONDS = 15.0
BLOCK_EVENT_SECONDS = 5.0

ProcessKey = tuple[int, float]


class AppControlModule:
    def __init__(
        self,
        store: PolicyStore,
        clock: TrustedClock,
        apps: AppState,
        enforcement: Enforcement,
        bus: Bus,
        platform: ModuleType,
        queue: EventQueue | None = None,
        session: DeviceSession | None = None,
        screen: ScreenState | None = None,
        hashes: HashCache | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        interval: float = TICK_SECONDS,
    ) -> None:
        self._store = store
        self._clock = clock
        self._apps = apps
        self._enforcement = enforcement
        self._platform = platform
        self._queue = queue
        self._device = session
        self._screen = screen
        self._hashes = hashes or HashCache(platform.read_chunks)
        self._monotonic = monotonic
        self._interval = interval
        self._user: SessionInfo | None = None
        self._screen_locked = False
        self._seen: set[ProcessKey] = set()
        self._scope: tuple | None = None
        self._last_block_event: dict[str, float] = {}
        self._last_ping: float | None = None
        self._idle: float | None = None
        self._foreground: str | None = None
        self._current: tuple[int, str] | None = None
        self._current_policy: EffectivePolicy | None = None
        self._started: float = 0.0
        bus.subscribe(SESSION, self._on_session)
        bus.subscribe(TRAY_HEARTBEAT, self._on_ping)

    def _on_session(self, event: SessionEvent) -> None:
        if event.kind in ("logon", "unlock"):
            self._user = self._platform.current_session()
            self._screen_locked = False
        elif event.kind == "lock":
            self._screen_locked = True
        elif event.kind == "logoff":
            self._user = None
            self._screen_locked = False

    def _on_ping(self, ping: TrayPing) -> None:
        self._last_ping = self._monotonic()
        self._idle = ping.idle_seconds
        self._foreground = ping.foreground

    def start(self) -> None:
        self._user = self._platform.current_session()

    async def run(self) -> None:
        self.start()
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("app control tick failed")
            await asyncio.sleep(self._interval)

    def _child(self) -> int | None:
        if self._user is None:
            return None
        return self._store.child_for_sid(self._user.sid)

    async def tick(self) -> None:
        now = self._monotonic()
        child = self._child()
        policy = None if child is None else self._store.rules_for(child)
        await self._track_foreground(child, policy, now)
        if child is None or policy is None or self._user is None:
            self._scope = None
            self._seen.clear()
            return
        if not self._enforcement.enabled:
            self._scope = None
            self._seen.clear()
            return
        scope = (child, policy.version, policy.source, self._user.session_id)
        if scope != self._scope:
            self._scope = scope
            self._seen.clear()
        await self._scan(child, policy, self._user.session_id, now)

    async def _scan(self, child: int, policy: EffectivePolicy, session_id: int, now: float) -> None:
        processes = await asyncio.to_thread(self._platform.list_processes)
        alive = {(p.pid, p.create_time) for p in processes}
        self._seen &= alive
        app_rules = policy.rules["app_rules"]
        if not app_rules:
            self._seen = alive
            return
        dirs = self._platform.protected_dirs()
        for proc in processes:
            key = (proc.pid, proc.create_time)
            if key in self._seen:
                continue
            self._seen.add(key)
            if is_protected(proc, session_id, dirs):
                continue
            if await self._should_block(proc, app_rules):
                await self._block(child, policy, proc, now)

    async def _should_block(self, proc: ProcInfo, app_rules: list[dict]) -> bool:
        if blocked_by_name(proc.name, app_rules):
            return True
        if not has_hash_rules(app_rules):
            return False
        sha256 = await asyncio.to_thread(self._hashes.get, proc.exe)
        if sha256 is None and proc.exe:
            log.warning("cannot hash %s (%s); blocking it because the policy has hash rules", proc.name, proc.exe)
            return True
        return decide(proc.name, sha256, app_rules) == BLOCK

    async def _block(self, child: int, policy: EffectivePolicy, proc: ProcInfo, now: float) -> None:
        killed = await asyncio.to_thread(self._platform.terminate, proc.pid, proc.create_time)
        if not killed:
            log.warning("could not end blocked app %s (pid %s)", proc.name, proc.pid)
            return
        log.info("blocked %s (pid %s) for child %s", proc.name, proc.pid, child)
        self._apps.blocked(proc.name, policy.set_by, policy.source)
        last = self._last_block_event.get(proc.name)
        if last is not None and now - last < BLOCK_EVENT_SECONDS:
            return
        self._last_block_event[proc.name] = now
        await self._emit(child, policy, "blocked_app", proc.name, 0)

    def _visible_app(self, child: int | None, now: float) -> str | None:
        if child is None or self._screen_locked or self._foreground is None:
            return None
        if self._last_ping is None or now - self._last_ping > TRAY_STALE_SECONDS:
            return None
        if self._idle is not None and self._idle >= IDLE_LIMIT:
            return None
        if self._screen is not None and self._screen.state == STATE_LOCKED:
            return None
        return self._foreground

    async def _track_foreground(self, child: int | None, policy: EffectivePolicy | None, now: float) -> None:
        app = None if policy is None else self._visible_app(child, now)
        wanted = None if app is None else (child, app)
        if self._current is not None and self._current != wanted:
            await self._stop_current(now)
        if self._current is not None and now - self._started >= MAX_DURATION_SEC:
            cid, name = self._current
            await self._emit(cid, self._current_policy, "app_stop", name, MAX_DURATION_SEC)
            await self._emit(cid, self._current_policy, "app_start", name, 0)
            self._started += MAX_DURATION_SEC
        if self._current is None and wanted is not None:
            self._current, self._current_policy, self._started = wanted, policy, now
            await self._emit(child, policy, "app_start", app, 0)

    async def _stop_current(self, now: float) -> None:
        cid, name = self._current
        duration = min(int(now - self._started), MAX_DURATION_SEC)
        await self._emit(cid, self._current_policy, "app_stop", name, duration)
        self._current = None
        self._current_policy = None

    async def _emit(self, child: int, policy: EffectivePolicy, kind: str, subject: str, duration: int) -> None:
        device_id = None if self._device is None else self._device.device_id
        if self._queue is None or device_id is None:
            return
        event = {
            "ts": format_ts(self._clock.now()),
            "device_id": device_id,
            "child_id": child,
            "type": kind,
            "subject": subject,
            "duration_sec": max(0, duration),
            "policy_id": policy.version,
        }
        try:
            await self._queue.enqueue([event])
        except EventInvalid as exc:
            log.error("dropped %s event: invalid %s", kind, exc.field)


def create(context: ModuleContext) -> AppControlModule:
    return AppControlModule(
        context.policy_store,
        context.clock,
        context.apps,
        context.enforcement,
        context.bus,
        context.platform,
        context.event_queue,
        context.session,
        context.screen,
    )
