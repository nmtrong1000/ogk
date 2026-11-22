import asyncio
import logging

import pytest

from service.core.bus import SESSION, TRAY_HEARTBEAT, Bus, SessionEvent, SessionInfo, TrayPing
from service.core.enforcement import Enforcement
from service.modules.presence import PresenceMonitor


class FakeProcess:
    def __init__(self, pid):
        self.pid = pid
        self.running = True
        self.terminated = False

    def alive(self):
        return self.running

    def terminate(self):
        self.running = False
        self.terminated = True


DEFAULT_SESSION = SessionInfo(1, "an")


class FakePlatform:
    def __init__(self, session=DEFAULT_SESSION):
        self.session = session
        self.launched = []
        self.fail_launch = False
        self.die_at_start = False

    def current_session(self):
        return self.session

    def launch_tray(self, session_id):
        if self.fail_launch:
            raise OSError("access denied")
        process = FakeProcess(100 + len(self.launched))
        process.running = not self.die_at_start
        self.launched.append((session_id, process))
        return process


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def env():
    bus = Bus()
    enforcement = Enforcement()
    platform = FakePlatform()
    clock = Clock()
    monitor = PresenceMonitor(
        bus,
        enforcement,
        platform,
        check_interval=0.01,
        startup_grace=0,
        heartbeat_timeout=15,
        start_timeout=10,
        max_failures=3,
        retry_interval=30,
        clock=clock,
    )
    bus.publish(SESSION, SessionEvent("logon", 1))
    return bus, enforcement, platform, clock, monitor


def _heartbeat(bus, pid):
    bus.publish(TRAY_HEARTBEAT, TrayPing(pid))


@pytest.mark.anyio
async def test_launches_tray_in_active_session(env):
    bus, _, platform, _, monitor = env
    await monitor.tick()
    assert [s for s, _ in platform.launched] == [1]
    await monitor.tick()
    assert len(platform.launched) == 1


@pytest.mark.anyio
async def test_late_heartbeat_from_existing_tray_stops_duplicate_launch(env):
    bus, _, platform, _, monitor = env
    await monitor.tick()
    duplicate = platform.launched[0][1]

    _heartbeat(bus, 999)

    assert duplicate.terminated
    assert monitor._process is None
    await monitor.tick()
    assert len(platform.launched) == 1


@pytest.mark.anyio
async def test_killed_tray_is_launched_again(env, caplog):
    caplog.set_level(logging.INFO)
    bus, _, platform, clock, monitor = env
    await monitor.tick()
    first = platform.launched[0][1]
    _heartbeat(bus, first.pid)
    first.running = False
    clock.now += 1
    await monitor.tick()
    assert len(platform.launched) == 2
    assert "exited, launching again" in caplog.text
    assert monitor.failures == 0


@pytest.mark.anyio
async def test_repeated_failures_disable_enforcement(env, caplog):
    bus, enforcement, platform, clock, monitor = env
    platform.die_at_start = True
    for _ in range(3):
        await monitor.tick()
        clock.now += 1
        await monitor.tick()
    assert monitor.failures == 3
    assert enforcement.snapshot()["enabled"] is False
    assert enforcement.snapshot()["reason"] == "tray_unavailable"
    assert "enforcement disabled: tray_unavailable" in caplog.text
    launches = len(platform.launched)
    clock.now += 5
    await monitor.tick()
    assert len(platform.launched) == launches
    clock.now += 30
    await monitor.tick()
    assert len(platform.launched) == launches + 1


@pytest.mark.anyio
async def test_launch_errors_count_as_failures(env, caplog):
    _, enforcement, platform, clock, monitor = env
    platform.fail_launch = True
    for _ in range(3):
        await monitor.tick()
        clock.now += 1
    assert not enforcement.enabled
    assert "launch error: access denied" in caplog.text


@pytest.mark.anyio
async def test_no_heartbeat_within_start_timeout_is_a_failure(env):
    _, _, platform, clock, monitor = env
    await monitor.tick()
    process = platform.launched[0][1]
    clock.now += 10
    await monitor.tick()
    assert process.terminated
    assert monitor.failures == 1
    assert len(platform.launched) == 2


@pytest.mark.anyio
async def test_heartbeat_after_disable_enables_again(env, caplog):
    caplog.set_level(logging.INFO)
    bus, enforcement, platform, clock, monitor = env
    platform.fail_launch = True
    for _ in range(3):
        await monitor.tick()
    assert not enforcement.enabled
    platform.fail_launch = False
    clock.now += 30
    await monitor.tick()
    _heartbeat(bus, platform.launched[-1][1].pid)
    assert enforcement.enabled
    assert monitor.failures == 0
    assert "tray ui is up" in caplog.text


@pytest.mark.anyio
async def test_logoff_stops_tray_without_failure_and_logon_launches(env, caplog):
    caplog.set_level(logging.INFO)
    bus, enforcement, platform, clock, monitor = env
    await monitor.tick()
    process = platform.launched[0][1]
    _heartbeat(bus, process.pid)
    bus.publish(SESSION, SessionEvent("logoff", 1))
    await monitor.tick()
    assert process.terminated
    clock.now += 60
    await monitor.tick()
    assert len(platform.launched) == 1
    assert monitor.failures == 0 and enforcement.enabled
    _heartbeat(bus, process.pid)
    bus.publish(SESSION, SessionEvent("logon", 1))
    await monitor.tick()
    assert len(platform.launched) == 2
    assert "stopped: session 1 ended" in caplog.text
    assert "session logoff, id 1" in caplog.text
    assert "session logon, id 1" in caplog.text


@pytest.mark.anyio
async def test_lock_and_unlock_only_log(env, caplog):
    caplog.set_level(logging.INFO)
    bus, _, platform, _, monitor = env
    await monitor.tick()
    _heartbeat(bus, platform.launched[0][1].pid)
    bus.publish(SESSION, SessionEvent("lock", 1))
    bus.publish(SESSION, SessionEvent("unlock", 1))
    await monitor.tick()
    assert len(platform.launched) == 1
    assert not platform.launched[0][1].terminated
    assert "session lock, id 1" in caplog.text
    assert "session unlock, id 1" in caplog.text


@pytest.mark.anyio
async def test_fresh_heartbeat_from_unowned_tray_prevents_duplicate(env):
    bus, _, platform, clock, monitor = env
    _heartbeat(bus, 999)
    await monitor.tick()
    assert platform.launched == []
    clock.now += 15
    await monitor.tick()
    assert len(platform.launched) == 1


@pytest.mark.anyio
async def test_no_session_means_no_launch():
    platform = FakePlatform(session=None)
    monitor = PresenceMonitor(Bus(), Enforcement(), platform, check_interval=0.01, startup_grace=0)
    task = asyncio.create_task(monitor.run())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert platform.launched == []


@pytest.mark.anyio
async def test_run_uses_current_session_and_stops_tray_on_cancel():
    platform = FakePlatform()
    monitor = PresenceMonitor(Bus(), Enforcement(), platform, check_interval=0.01, startup_grace=0)
    task = asyncio.create_task(monitor.run())
    for _ in range(100):
        if platform.launched:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert platform.launched[0][0] == 1
    assert platform.launched[0][1].terminated


@pytest.mark.anyio
async def test_startup_grace_delays_first_launch():
    platform = FakePlatform()
    monitor = PresenceMonitor(Bus(), Enforcement(), platform, check_interval=0.01, startup_grace=60)
    task = asyncio.create_task(monitor.run())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert platform.launched == []
