"""Offline time is the larger of two measures. The monotonic measure adds up time.monotonic() deltas and is
saved in the DB, so changing the system clock cannot shrink it and a restart does not reset it. The wall
measure is the system clock minus the last server time; it also counts time the service was not running.
Moving the system clock back only lowers the wall measure, so the monotonic one still holds; moving it forward
only reaches the default policy sooner. simulated_seconds is added by the development tools only and is
not saved.
Methods are synchronous; async callers run them in a worker thread.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime

from service.core.local_db import LocalDb, SyncState


def utcnow() -> datetime:
    return datetime.now(UTC)


class SyncClock:
    def __init__(
        self,
        db: LocalDb,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], datetime] = utcnow,
    ) -> None:
        self._db = db
        self._monotonic = monotonic
        self._wall = wall
        self._state = SyncState()
        self._last_mono: float | None = None
        self.simulated_seconds = 0.0

    @property
    def last_server_time(self) -> datetime | None:
        return self._state.last_server_time

    def load(self) -> None:
        self._state = self._db.load_sync_state()
        self._last_mono = self._monotonic()

    def _elapsed(self) -> float:
        now = self._monotonic()
        last = now if self._last_mono is None else self._last_mono
        self._last_mono = now
        return max(0.0, now - last)

    def tick(self) -> float:
        elapsed = self._elapsed()
        self._state = SyncState(
            self._state.offline_seconds + elapsed, self._state.last_server_time, self._state.last_success_at
        )
        self._db.save_sync_state(self._state)
        return self.offline_seconds()

    def mark_online(self, server_time: datetime) -> None:
        self._elapsed()
        self._state = SyncState(0.0, server_time, self._wall())
        self.simulated_seconds = 0.0
        self._db.save_sync_state(self._state)

    def simulate(self, seconds: float) -> None:
        self.simulated_seconds += seconds

    def offline_seconds(self) -> float:
        measured = self._state.offline_seconds
        if self._state.last_server_time is not None:
            measured = max(measured, (self._wall() - self._state.last_server_time).total_seconds())
        return measured + self.simulated_seconds
