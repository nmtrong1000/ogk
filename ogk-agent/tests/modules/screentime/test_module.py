import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from service.core.alerts import AlertBoard
from service.core.bus import SESSION, TRAY_HEARTBEAT, Bus, SessionEvent, SessionInfo, TrayPing
from service.core.event_queue import EventQueue
from service.core.local_db import DB_FILE, LocalDb
from service.core.policy_store import PolicyStore
from service.core.screen_state import STATE_GRACE, STATE_LOCKED, STATE_NONE, STATE_OK, ScreenState
from service.core.trusted_clock import TrustedClock
from service.modules.screentime import ScreenTimeModule
from service.modules.screentime.counters import ChildCounter, CounterSet
from tests.core.test_default_policy import DEFAULT
from tests.policy_vectors import OPEN_DAY, body, document, write_public_key

pytestmark = pytest.mark.anyio

SID = "S-1-5-21-1000-1000-1000-1001"
OTHER_SID = "S-1-5-21-1000-1000-1000-1999"
THURSDAY_8AM = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)
CLOSED_DAY = "0" * 48


class FakePlatform:
    def __init__(self) -> None:
        self.user: SessionInfo | None = SessionInfo(1, "an", SID)

    def current_session(self) -> SessionInfo | None:
        return self.user


class FakeDevice:
    device_id = 3


class Rig:
    def __init__(self, data_dir, start: datetime = THURSDAY_8AM) -> None:
        self.data_dir = data_dir
        self.mono = 1000.0
        self.wall = start
        self.db = LocalDb(data_dir)
        self.store = PolicyStore(self.db, write_public_key(data_dir), DEFAULT)
        self.bus = Bus()
        self.platform = FakePlatform()
        self.screen = ScreenState()
        self.alerts = AlertBoard()
        self.queue = EventQueue(self.db, None)
        self.module = self._module()

    def _module(self) -> ScreenTimeModule:
        self.clock = TrustedClock(self.db, lambda: self.mono, lambda: self.wall, tz=UTC)
        return ScreenTimeModule(
            self.store,
            self.clock,
            CounterSet(self.db, [ChildCounter()]),
            self.screen,
            self.alerts,
            self.bus,
            self.platform,
            self.queue,
            FakeDevice(),
            monotonic=lambda: self.mono,
        )

    def policy(self, version: int = 1, quota: int = 120, **kwargs) -> None:
        self.store.save(body(document(7, version, quota, accounts=[SID], **kwargs)))

    async def start(self) -> None:
        await self.module.start()
        await self.module.tick()

    async def run(self, seconds: int) -> None:
        for _ in range(seconds):
            self.mono += 1
            self.wall += timedelta(seconds=1)
            await self.module.tick()

    async def restart(self) -> None:
        self.bus = Bus()
        self.screen = ScreenState()
        self.module = self._module()
        await self.start()

    def session(self, kind: str) -> None:
        self.bus.publish(SESSION, SessionEvent(kind, 1))

    def events(self) -> list[dict]:
        with sqlite3.connect(self.data_dir / DB_FILE) as conn:
            rows = conn.execute("SELECT payload FROM event_outbox ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]


@pytest.fixture
def rig(data_dir):
    return Rig(data_dir)


async def test_three_minute_quota_locks_after_grace(rig):
    rig.policy(quota=3, schedule=[OPEN_DAY] * 7)
    await rig.start()
    assert rig.screen.state == STATE_OK
    assert rig.screen.remaining_seconds == 180
    await rig.run(180)
    assert (rig.screen.state, rig.screen.grace_seconds, rig.screen.lock_reason) == (STATE_GRACE, 60, "quota")
    assert rig.screen.lock_seq == 0
    await rig.run(59)
    assert rig.screen.state == STATE_GRACE
    await rig.run(1)
    assert (rig.screen.state, rig.screen.lock_seq) == (STATE_LOCKED, 1)
    assert rig.screen.set_by == "parent@example.com"
    types = [(e["type"], e["subject"]) for e in rig.events()]
    assert types == [("quota_warning", "1"), ("locked", "quota")]
    locked = rig.events()[-1]
    assert (locked["device_id"], locked["child_id"], locked["policy_id"]) == (3, 7, 1)
    assert locked["duration_sec"] == 240


async def test_all_three_warnings_before_lock(rig):
    rig.policy(quota=11, schedule=[OPEN_DAY] * 7)
    await rig.start()
    seen = []
    for _ in range(11 * 60):
        before = rig.screen.warning_seq
        await rig.run(1)
        if rig.screen.warning_seq != before:
            seen.append(rig.screen.warning)
    assert seen == [10, 5, 1]
    assert rig.screen.state == STATE_GRACE
    assert [e["subject"] for e in rig.events() if e["type"] == "quota_warning"] == ["10", "5", "1"]


async def test_outside_schedule_locks_within_five_seconds(rig):
    rig.policy(schedule=[CLOSED_DAY] * 7)
    await rig.start()
    assert (rig.screen.state, rig.screen.lock_reason, rig.screen.lock_seq) == (STATE_LOCKED, "schedule", 1)
    assert [(e["type"], e["subject"]) for e in rig.events()] == [("locked", "schedule")]


async def test_schedule_end_warns_then_locks(data_dir):
    rig = Rig(data_dir, start=THURSDAY_8AM.replace(hour=20, minute=49))
    allowed_until_21 = "1" * 42 + "0" * 6
    rig.policy(quota=600, schedule=[allowed_until_21] * 7)
    await rig.start()
    assert rig.screen.remaining_seconds == 660
    await rig.run(660)
    assert (rig.screen.state, rig.screen.lock_reason) == (STATE_GRACE, "schedule")
    await rig.run(60)
    assert rig.screen.state == STATE_LOCKED
    assert [e["subject"] for e in rig.events() if e["type"] == "quota_warning"] == ["10", "5", "1"]


async def test_new_policy_closing_now_locks_within_five_seconds(rig):
    rig.policy(schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(10)
    rig.policy(version=2, schedule=[CLOSED_DAY] * 7)
    await rig.run(1)
    assert rig.screen.state == STATE_GRACE
    rig.policy(version=3, schedule=[OPEN_DAY] * 7)
    await rig.run(1)
    assert rig.screen.state == STATE_OK


async def test_unlock_while_out_of_time_locks_again(rig):
    rig.policy(quota=0, schedule=[OPEN_DAY] * 7)
    await rig.start()
    assert (rig.screen.state, rig.screen.lock_seq) == (STATE_LOCKED, 1)
    rig.session("lock")
    await rig.run(30)
    assert rig.screen.lock_seq == 1
    rig.session("unlock")
    await rig.run(1)
    assert rig.screen.lock_seq == 2
    rig.session("logoff")
    rig.session("logon")
    await rig.run(1)
    assert rig.screen.lock_seq == 3
    assert [e["type"] for e in rig.events()] == ["locked", "locked", "locked"]


async def test_lock_order_repeats_while_session_stays_unlocked(rig):
    rig.policy(quota=0, schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(5)
    assert rig.screen.lock_seq == 2
    await rig.run(5)
    assert rig.screen.lock_seq == 3
    assert len(rig.events()) == 1


async def test_locked_and_idle_time_not_counted(rig):
    rig.policy(schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(60)
    rig.session("lock")
    await rig.run(600)
    rig.session("unlock")
    rig.bus.publish(TRAY_HEARTBEAT, TrayPing(42, 301.0))
    await rig.run(10)
    assert rig.screen.counting is False
    rig.bus.publish(TRAY_HEARTBEAT, TrayPing(42, 2.0))
    await rig.run(10)
    assert rig.screen.used_seconds == 70


async def test_stale_tray_heartbeat_counts_time(rig):
    rig.policy(schedule=[OPEN_DAY] * 7)
    await rig.start()
    rig.bus.publish(TRAY_HEARTBEAT, TrayPing(42, 900.0))
    await rig.run(10)
    assert rig.screen.used_seconds == 0
    await rig.run(20)
    assert rig.screen.used_seconds > 0


async def test_large_monotonic_jump_counts_at_most_two_seconds(rig):
    rig.policy(schedule=[OPEN_DAY] * 7)
    await rig.start()
    rig.mono += 3600
    await rig.module.tick()
    assert rig.screen.used_seconds == 2


async def test_unmapped_account_is_not_enforced(rig):
    rig.policy(quota=0, schedule=[CLOSED_DAY] * 7)
    rig.platform.user = SessionInfo(1, "parent", OTHER_SID)
    await rig.start()
    await rig.run(10)
    assert (rig.screen.state, rig.screen.lock_seq, rig.screen.child_id) == (STATE_NONE, 0, None)
    assert rig.events() == []


async def test_restart_keeps_minutes_used(rig):
    rig.policy(schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(95)
    await rig.restart()
    assert rig.screen.used_seconds >= 90


async def test_new_trusted_day_resets_usage(data_dir):
    rig = Rig(data_dir, start=THURSDAY_8AM.replace(hour=23, minute=58, second=0))
    rig.policy(quota=1, schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(61)
    assert rig.screen.state == STATE_GRACE
    await rig.run(60)
    assert rig.screen.state == STATE_OK
    assert rig.screen.used_seconds < 15


async def test_setting_clock_back_three_hours_adds_no_quota(rig):
    rig.policy(quota=3, schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(120)
    remaining = rig.screen.remaining_seconds
    rig.wall -= timedelta(hours=3)
    await rig.run(1)
    assert rig.screen.remaining_seconds == remaining - 1
    assert [(a.type, a.detail) for a in rig.alerts.active()] == [("clock_tampered", "backward")]
    await rig.restart()
    assert rig.screen.remaining_seconds <= remaining
    await rig.run(120)
    assert rig.screen.state in (STATE_GRACE, STATE_LOCKED)
    rig.wall = rig.clock.now()
    await rig.run(1)
    assert rig.alerts.active() == []


async def test_setting_clock_back_across_midnight_keeps_today(data_dir):
    rig = Rig(data_dir, start=THURSDAY_8AM.replace(hour=0, minute=30))
    rig.policy(quota=1, schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(130)
    assert rig.screen.state == STATE_LOCKED
    rig.wall -= timedelta(hours=3)
    await rig.run(5)
    assert rig.screen.state == STATE_LOCKED
    assert rig.screen.used_seconds >= 60


async def test_used_today_feeds_heartbeat(rig):
    rig.policy(schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.run(42)
    assert rig.screen.used_today == {7: 42}


async def test_parent_unlock_override_prevents_immediate_relock(rig):
    rig.policy(quota=0, schedule=[OPEN_DAY] * 7)
    await rig.start()
    assert rig.screen.state == STATE_LOCKED
    await rig.module.execute_command({"id": 1, "child_id": 7, "type": "unlock", "minutes": 0})
    await rig.module.tick()
    assert rig.screen.state == STATE_OK
    assert rig.screen.override is True
    assert rig.screen.lock_seq > 1


async def test_add_time_grants_15_active_minutes_even_at_zero_quota(rig):
    rig.policy(quota=0, schedule=[OPEN_DAY] * 7)
    await rig.start()
    await rig.module.execute_command({"id": 2, "child_id": 7, "type": "add_time", "minutes": 15})
    await rig.module.tick()
    assert rig.screen.state == STATE_OK
    assert rig.screen.remaining_seconds == 900
    await rig.run(30)
    assert rig.screen.remaining_seconds == 870
