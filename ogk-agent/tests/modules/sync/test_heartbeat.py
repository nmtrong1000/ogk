import asyncio
from datetime import timedelta
from functools import partial

import pytest

from service.core.alerts import AlertBoard
from service.core.bus import SERVER_TIME, Bus
from service.core.clock import SyncClock
from service.core.device_session import DeviceSession
from service.core.enforcement import Enforcement
from service.core.event_queue import EventQueue
from service.core.local_db import LocalDb
from service.core.offline import OfflineGuard
from service.core.policy_store import MODE_CACHED, MODE_DEFAULT, PolicyStore
from service.core.screen_state import ScreenState
from service.modules.policy import PolicyLoader
from service.modules.sync import SyncModule
from service.modules.sync.heartbeat import USAGE_DAYS
from tests.core.test_default_policy import DEFAULT
from tests.core.test_device_session import CONFIG, enrolled
from tests.fake_server import FakeServer
from tests.policy_vectors import EVENT_VECTORS, body, document, write_public_key

pytestmark = pytest.mark.anyio


class Rig:
    def __init__(self, data_dir) -> None:
        self.server = FakeServer()
        self.mono = 0.0
        db = LocalDb(data_dir)
        self.db = db
        enrolled(self.server, db)
        self.session = DeviceSession(CONFIG, db, client_factory=self.server.client, clock=lambda: self.server.now)
        self.bus = Bus()
        self.store = PolicyStore(db, write_public_key(data_dir), DEFAULT)
        clock = SyncClock(db, monotonic=lambda: self.mono, wall=lambda: self.server.now)
        self.offline = OfflineGuard(clock, self.store, self.bus, 7)
        self.offline.start()
        self.enforcement = Enforcement()
        self.queue = EventQueue(db, self.session)
        self.loader = PolicyLoader(self.store, self.session, self.bus)
        self.screen = ScreenState()
        self.alerts = AlertBoard()
        self.sync = SyncModule(
            self.session,
            self.queue,
            self.offline,
            self.store,
            self.enforcement,
            self.bus,
            interval=0.01,
            screen=self.screen,
            alerts=self.alerts,
            usage=partial(db.recent_usage, USAGE_DAYS),
        )

    def publish_policy(self, version: int, quota: int) -> None:
        self.server.policy_body = body(document(7, version, quota=quota))
        self.server.versions = {7: version}

    def pass_time(self, seconds: float) -> None:
        self.mono += seconds
        self.server.now += timedelta(seconds=seconds)


@pytest.fixture
def rig(data_dir):
    return Rig(data_dir)


async def run_until(predicate, task_factories, timeout: float = 2.0) -> None:
    tasks = [asyncio.create_task(factory()) for factory in task_factories]
    try:
        async with asyncio.timeout(timeout):
            while not predicate():
                await asyncio.sleep(0.01)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_policy_edit_reaches_agent_on_next_heartbeat(rig):
    rig.publish_policy(1, 120)
    await run_until(lambda: rig.store.versions() == {7: 1}, [rig.loader.run, rig.sync.run])
    rig.publish_policy(2, 45)
    await run_until(lambda: rig.store.versions() == {7: 2}, [rig.loader.run, rig.sync.run])
    assert rig.store.rules_for(7).rules["weekday_quota_minutes"] == 45


async def test_heartbeat_body_reports_versions_and_mode(rig):
    rig.publish_policy(3, 120)
    await rig.loader.tick()
    assert await rig.sync.tick()
    sent = rig.server.heartbeats[-1]
    assert sent["policy_versions"] == {"7": 3}
    assert sent["quota_used"] == {"7": 0}
    assert sent["status"]["policy_mode"] == MODE_CACHED
    assert sent["alerts"] == []


async def test_enforcement_disabled_sends_alert(rig):
    rig.enforcement.disable("tray_unavailable")
    await rig.sync.tick()
    (alert,) = rig.server.heartbeats[-1]["alerts"]
    assert alert["type"] == "enforcement_disabled"
    assert alert["detail"] == "tray_unavailable"
    assert alert["ts"] == rig.enforcement.since
    rig.enforcement.enable()
    await rig.sync.tick()
    assert rig.server.heartbeats[-1]["alerts"] == []


async def test_quota_used_and_clock_alert_are_sent(rig):
    rig.publish_policy(3, 120)
    await rig.loader.tick()
    rig.screen.used_today = {7: 1234}
    rig.alerts.raise_("clock_tampered", "backward", rig.server.now)
    await rig.sync.tick()
    sent = rig.server.heartbeats[-1]
    assert sent["quota_used"] == {"7": 1234}
    assert [(a["type"], a["detail"]) for a in sent["alerts"]] == [("clock_tampered", "backward")]


async def test_usage_days_send_stored_days_and_todays_live_value(rig):
    for day in range(10, 20):
        rig.db.save_usage(f"2026-11-{day:02}", {(7, "child"): 100.0 * day, (7, "group:games"): 5.0}, rig.server.now)
    rig.screen.used_today = {7: 2500, 8: 40}
    rig.screen.usage_day = "2026-11-19"
    await rig.sync.tick()
    sent = rig.server.heartbeats[-1]["usage_days"]
    assert [(u["child_id"], u["day"]) for u in sent] == [(7, f"2026-11-{day:02}") for day in range(13, 19)] + [
        (7, "2026-11-19"),
        (8, "2026-11-19"),
    ]
    assert sent[0]["seconds"] == 1300
    assert [u["seconds"] for u in sent if u["day"] == "2026-11-19"] == [2500, 40]


async def test_usage_days_empty_without_any_usage(rig):
    await rig.sync.tick()
    assert rig.server.heartbeats[-1]["usage_days"] == []


async def test_heartbeat_outcome_published_as_server_time(rig):
    seen = []
    rig.bus.subscribe(SERVER_TIME, seen.append)
    await rig.sync.tick()
    rig.server.offline = True
    await rig.sync.tick()
    assert seen == [rig.server.now, None]


async def test_tick_flushes_queued_events(rig):
    await rig.queue.enqueue([EVENT_VECTORS["valid"][0]["event"]])
    await rig.sync.tick()
    assert len(rig.server.events) == 1
    assert rig.server.requests.index(("POST", "/api/device/events")) < rig.server.requests.index(
        ("POST", "/api/device/heartbeat")
    )


async def test_events_survive_outage_and_are_sent_once(rig):
    sample = EVENT_VECTORS["valid"][0]["event"]
    await rig.queue.enqueue([sample, sample])
    rig.server.offline = True
    assert not await rig.sync.tick()
    rig.server.offline = False
    rig.server.drop_response = True
    await rig.sync.tick()
    rig.server.drop_response = False
    await rig.sync.tick()
    await rig.sync.tick()
    assert len(rig.server.events) == 2
    assert await rig.queue.pending() == 0


async def test_seven_days_offline_switches_to_default_policy(rig):
    rig.publish_policy(3, 45)
    await rig.loader.tick()
    await rig.sync.tick()
    rig.server.offline = True
    for _ in range(6):
        rig.pass_time(86400)
        await rig.sync.tick()
    assert rig.store.mode == MODE_CACHED
    rig.pass_time(86400)
    await rig.sync.tick()
    assert rig.store.mode == MODE_DEFAULT
    assert rig.store.rules_for(7).rules == DEFAULT.rules
    rig.server.offline = False
    await rig.sync.tick()
    assert rig.store.mode == MODE_CACHED
    assert rig.store.rules_for(7).rules["weekday_quota_minutes"] == 45


async def test_unenrolled_device_does_not_send(data_dir):
    db = LocalDb(data_dir)
    session = DeviceSession(CONFIG, db, client_factory=FakeServer().client)
    store = PolicyStore(db, write_public_key(data_dir), DEFAULT)
    guard = OfflineGuard(SyncClock(db), store, Bus(), 7)
    guard.start()
    module = SyncModule(session, EventQueue(db, session), guard, store, Enforcement(), Bus(), 0.01)
    assert not await module.tick()
