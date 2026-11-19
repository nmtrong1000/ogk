from datetime import UTC, datetime

from service.core.local_db import LocalDb
from service.modules.screentime.counters import Activity, ChildCounter, CounterSet

NOW = datetime(2026, 11, 19, 8, tzinfo=UTC)


class ForegroundCounter:
    name = "app_group:games"

    def counts(self, activity: Activity) -> bool:
        return activity.active and activity.foreground == "game.exe"


def test_saved_usage_survives_restart(data_dir):
    counters = CounterSet(LocalDb(data_dir), [ChildCounter()])
    counters.open_day("2026-11-19")
    counters.record(Activity(7, True), 90.5)
    counters.record(Activity(7, False), 30)
    counters.save(NOW)
    restarted = CounterSet(LocalDb(data_dir), [ChildCounter()])
    restarted.open_day("2026-11-19")
    assert restarted.used(7) == 90.5


def test_new_day_starts_at_zero_and_keeps_old_day(data_dir):
    counters = CounterSet(LocalDb(data_dir), [ChildCounter()])
    counters.open_day("2026-11-19")
    counters.record(Activity(7, True), 60)
    counters.save(NOW)
    counters.open_day("2026-11-20")
    assert counters.used(7) == 0
    counters.open_day("2026-11-19")
    assert counters.used(7) == 60


def test_several_counters_share_one_set(data_dir):
    counters = CounterSet(LocalDb(data_dir), [ChildCounter(), ForegroundCounter()])
    counters.open_day("2026-11-19")
    counters.record(Activity(7, True, "game.exe"), 10)
    counters.record(Activity(7, True, "word.exe"), 5)
    assert counters.used(7) == 15
    assert counters.used(7, "app_group:games") == 10
    assert counters.by_child() == {7: 15}
