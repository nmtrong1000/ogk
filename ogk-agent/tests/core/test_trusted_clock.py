from datetime import UTC, datetime, timedelta

from service.core.local_db import LocalDb
from service.core.trusted_clock import BACKWARD, FORWARD, TrustedClock

START = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)


class Clocks:
    def __init__(self) -> None:
        self.mono = 100.0
        self.wall = START

    def advance(self, seconds: float) -> None:
        self.mono += seconds
        self.wall += timedelta(seconds=seconds)


def make(data_dir, clocks: Clocks) -> TrustedClock:
    clock = TrustedClock(LocalDb(data_dir), lambda: clocks.mono, lambda: clocks.wall, tz=UTC)
    clock.load()
    return clock


def test_follows_monotonic_time(data_dir):
    clocks = Clocks()
    clock = make(data_dir, clocks)
    clocks.advance(90)
    assert clock.now() == START + timedelta(seconds=90)
    assert clock.check() is None


def test_setting_clock_back_is_tampering_and_ignored(data_dir):
    clocks = Clocks()
    clock = make(data_dir, clocks)
    clocks.wall -= timedelta(hours=3)
    clocks.advance(10)
    assert clock.check() == BACKWARD
    assert clock.now() == START + timedelta(seconds=10)
    clocks.wall = clock.now()
    assert clock.check() is None


def test_restart_after_setting_clock_back_keeps_saved_time(data_dir):
    clocks = Clocks()
    clock = make(data_dir, clocks)
    clocks.advance(600)
    clock.save()
    clocks.wall -= timedelta(hours=3)
    restarted = make(data_dir, clocks)
    assert restarted.now() == START + timedelta(seconds=600)
    assert restarted.check() == BACKWARD


def test_server_time_becomes_anchor(data_dir):
    clocks = Clocks()
    clock = make(data_dir, clocks)
    clock.online(START + timedelta(seconds=30))
    assert clock.now() == START + timedelta(seconds=30)
    assert clock.check() is None


def test_forward_jump_online_is_judged_by_server_time(data_dir):
    clocks = Clocks()
    clock = make(data_dir, clocks)
    clock.online(START)
    clocks.wall += timedelta(days=1)
    assert clock.check() is None
    assert clock.now() == START
    clock.online(START + timedelta(seconds=60))
    assert clock.check() == FORWARD
    assert clock.now() == START + timedelta(seconds=60)
    clocks.wall = START + timedelta(seconds=60)
    clock.online(START + timedelta(seconds=60))
    assert clock.check() is None


def test_forward_jump_offline_is_taken_as_sleep(data_dir):
    clocks = Clocks()
    clock = make(data_dir, clocks)
    clock.offline()
    clocks.wall += timedelta(hours=8)
    assert clock.check() is None
    assert clock.now() == START + timedelta(hours=8)
