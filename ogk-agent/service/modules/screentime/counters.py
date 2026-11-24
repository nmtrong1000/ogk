"""A counter decides from an Activity whether a tick counts; CounterSet owns the day and persistence for all of
them, so a later per-app-group counter only implements UsageCounter and joins the set. Values are kept in
memory and written by save(); the module saves every 30 seconds and on lock or logoff, so a crash loses at
most that much. Methods that touch the DB are synchronous; async callers run them in a worker thread.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from service.core.local_db import CHILD_COUNTER, LocalDb

__all__ = ["CHILD_COUNTER", "Activity", "ChildCounter", "CounterSet", "UsageCounter"]


@dataclass(frozen=True)
class Activity:
    child_id: int
    active: bool
    foreground: str | None = None


class UsageCounter(Protocol):
    name: str

    def counts(self, activity: Activity) -> bool: ...


class ChildCounter:
    name = CHILD_COUNTER

    def counts(self, activity: Activity) -> bool:
        return activity.active


class CounterSet:
    def __init__(self, db: LocalDb, counters: list[UsageCounter]) -> None:
        self._db = db
        self._counters = list(counters)
        self._values: dict[tuple[int, str], float] = {}
        self._dirty = False
        self.day: str | None = None

    def open_day(self, day: str) -> None:
        self._values = self._db.load_usage(day)
        self._dirty = False
        self.day = day

    def save(self, at: datetime) -> None:
        if self.day is not None and self._dirty:
            self._db.save_usage(self.day, self._values, at)
            self._dirty = False

    def record(self, activity: Activity, seconds: float) -> None:
        if seconds <= 0:
            return
        for counter in self._counters:
            if counter.counts(activity):
                key = (activity.child_id, counter.name)
                self._values[key] = self._values.get(key, 0.0) + seconds
                self._dirty = True

    def forget(self, child_id: int) -> None:
        self._values = {key: value for key, value in self._values.items() if key[0] != child_id}

    def used(self, child_id: int, counter: str = CHILD_COUNTER) -> float:
        return self._values.get((child_id, counter), 0.0)

    def by_child(self, counter: str = CHILD_COUNTER) -> dict[int, float]:
        return {child_id: seconds for (child_id, name), seconds in self._values.items() if name == counter}
