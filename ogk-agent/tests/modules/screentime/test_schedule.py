from datetime import UTC, datetime

from service.modules.screentime.schedule import allowed, quota_minutes, seconds_until_closed
from tests.policy_vectors import ALLOWED_DAY, OPEN_DAY, rules

CLOSED_DAY = "0" * 48
MONDAY = datetime(2026, 11, 16, tzinfo=UTC)


def at(day_offset: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return MONDAY.replace(day=16 + day_offset, hour=hour, minute=minute, second=second)


def test_index_zero_is_monday():
    schedule = [OPEN_DAY] + [CLOSED_DAY] * 6
    assert allowed(schedule, at(0, 10))
    assert not allowed(schedule, at(1, 10))
    assert not allowed(schedule, at(6, 10))


def test_slot_boundaries():
    schedule = [ALLOWED_DAY] * 7
    assert not allowed(schedule, at(0, 6, 59, 59))
    assert allowed(schedule, at(0, 7, 0, 0))
    assert allowed(schedule, at(0, 20, 59, 59))
    assert not allowed(schedule, at(0, 21, 0, 0))


def test_seconds_until_closed():
    schedule = [ALLOWED_DAY] * 7
    assert seconds_until_closed(schedule, at(0, 20, 0)) == 3600
    assert seconds_until_closed(schedule, at(0, 20, 45, 30)) == 870
    assert seconds_until_closed(schedule, at(0, 22, 0)) == 0


def test_open_block_runs_across_midnight():
    late = "0" * 44 + "1" * 4
    early = "1" * 2 + "0" * 46
    schedule = [late, early] + [CLOSED_DAY] * 5
    assert seconds_until_closed(schedule, at(0, 23, 0)) == 7200


def test_always_open_is_capped_at_a_week():
    assert seconds_until_closed([OPEN_DAY] * 7, at(2, 12)) == 7 * 24 * 3600


def test_weekend_quota_on_saturday_and_sunday():
    policy_rules = rules(60, weekend=180)
    assert quota_minutes(policy_rules, at(4, 12).date()) == 60
    assert quota_minutes(policy_rules, at(5, 12).date()) == 180
    assert quota_minutes(policy_rules, at(6, 12).date()) == 180
