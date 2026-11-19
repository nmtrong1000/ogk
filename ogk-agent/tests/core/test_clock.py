from datetime import UTC, datetime, timedelta

from service.core.clock import SyncClock
from service.core.local_db import LocalDb

START = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)


class Clocks:
    def __init__(self) -> None:
        self.mono = 1000.0
        self.wall = START

    def advance(self, seconds: float) -> None:
        self.mono += seconds
        self.wall += timedelta(seconds=seconds)


def make_clock(data_dir, clocks: Clocks) -> SyncClock:
    clock = SyncClock(LocalDb(data_dir), monotonic=lambda: clocks.mono, wall=lambda: clocks.wall)
    clock.load()
    return clock


def test_accumulates_offline_time(data_dir):
    clocks = Clocks()
    clock = make_clock(data_dir, clocks)
    clocks.advance(60)
    assert clock.tick() == 60
    clocks.advance(90)
    assert clock.tick() == 150


def test_mark_online_resets_and_stores_server_time(data_dir):
    clocks = Clocks()
    clock = make_clock(data_dir, clocks)
    clocks.advance(600)
    clock.tick()
    clock.mark_online(clocks.wall)
    assert clock.offline_seconds() == 0
    assert clock.last_server_time == clocks.wall


def test_offline_time_survives_restart(data_dir):
    clocks = Clocks()
    clock = make_clock(data_dir, clocks)
    clocks.advance(3600)
    clock.tick()
    clocks.mono = 5.0
    restarted = make_clock(data_dir, clocks)
    assert restarted.offline_seconds() == 3600
    clocks.mono += 60
    assert restarted.tick() == 3660


def test_moving_system_clock_back_does_not_shrink_offline_time(data_dir):
    clocks = Clocks()
    clock = make_clock(data_dir, clocks)
    clock.mark_online(clocks.wall)
    clocks.advance(2 * 86400)
    clock.tick()
    clocks.wall -= timedelta(days=30)
    assert clock.offline_seconds() == 2 * 86400


def test_wall_measure_counts_time_the_service_was_off(data_dir):
    clocks = Clocks()
    clock = make_clock(data_dir, clocks)
    clock.mark_online(clocks.wall)
    clocks.wall += timedelta(days=3)
    clocks.mono = 1.0
    restarted = make_clock(data_dir, clocks)
    assert restarted.offline_seconds() == 3 * 86400


def test_simulated_time_is_added_and_cleared_when_online(data_dir):
    clocks = Clocks()
    clock = make_clock(data_dir, clocks)
    clock.simulate(7 * 86400)
    assert clock.offline_seconds() == 7 * 86400
    clock.mark_online(clocks.wall)
    assert clock.offline_seconds() == 0
