import asyncio
from datetime import timedelta

import pytest

from service.core.bus import Bus
from service.core.clock import SyncClock
from service.core.device_session import DeviceSession
from service.core.enforcement import Enforcement
from service.core.event_queue import EventQueue
from service.core.local_db import LocalDb
from service.core.offline import OfflineGuard
from service.core.policy_store import MODE_CACHED, MODE_DEFAULT, PolicyStore
from service.modules.policy import PolicyLoader
from service.modules.sync import SyncModule
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
        self.sync = SyncModule(
            self.session, self.queue, self.offline, self.store, self.enforcement, self.bus, interval=0.01
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
    assert rig.store.rules_for(7).rules == {"daily_quota_minutes": 45}


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
    assert rig.store.rules_for(7).rules == {"daily_quota_minutes": 45}


async def test_unenrolled_device_does_not_send(data_dir):
    db = LocalDb(data_dir)
    session = DeviceSession(CONFIG, db, client_factory=FakeServer().client)
    store = PolicyStore(db, write_public_key(data_dir), DEFAULT)
    guard = OfflineGuard(SyncClock(db), store, Bus(), 7)
    guard.start()
    module = SyncModule(session, EventQueue(db, session), guard, store, Enforcement(), Bus(), 0.01)
    assert not await module.tick()
