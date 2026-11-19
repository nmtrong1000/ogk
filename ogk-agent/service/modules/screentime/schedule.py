"""weekly_schedule index 0 is Monday, matching date.weekday(); slot k covers [k*30 min, (k+1)*30 min) local time.
seconds_until_closed walks across midnight, so a block running from 23:00 Monday into Tuesday is one block.
"""

from datetime import date, datetime

SLOT_SECONDS = 1800
SLOTS_PER_DAY = 48
WEEKEND = (5, 6)
WEEK_SECONDS = 7 * 24 * 3600


def quota_minutes(rules: dict, day: date) -> int:
    return rules["weekend_quota_minutes"] if day.weekday() in WEEKEND else rules["weekday_quota_minutes"]


def _slot(at: datetime) -> int:
    return (at.hour * 3600 + at.minute * 60 + at.second) // SLOT_SECONDS


def allowed(schedule: list[str], at: datetime) -> bool:
    return schedule[at.weekday()][_slot(at)] == "1"


def seconds_until_closed(schedule: list[str], at: datetime) -> int:
    if not allowed(schedule, at):
        return 0
    total = SLOT_SECONDS - (at.minute * 60 + at.second) % SLOT_SECONDS
    day, slot = at.weekday(), _slot(at)
    while total < WEEK_SECONDS:
        slot += 1
        if slot == SLOTS_PER_DAY:
            day, slot = (day + 1) % 7, 0
        if schedule[day][slot] != "1":
            return total
        total += SLOT_SECONDS
    return WEEK_SECONDS


def day_key(at: datetime) -> str:
    return at.date().isoformat()
