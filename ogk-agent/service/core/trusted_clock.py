"""Screen time reads the time of day from this clock, never from the system clock directly. now() is an anchor
plus time.monotonic() elapsed since it was set, so changing the system clock does not move it.
The anchor is the last server_time while online. On start it is the later of the system clock and the last
saved trusted time, so moving the clock back and restarting does not move time back.
Backward: the system clock behind trusted time by more than the tolerance is tampering at once.
Forward: while the last heartbeat succeeded, a system clock ahead of trusted time is only judged at the next
server_time, because waking from sleep looks the same until then (monotonic time may not count sleep).
While offline nothing can tell the two apart, so a forward jump is accepted as sleep and becomes the anchor.
Methods are synchronous; async callers run them in a worker thread.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, tzinfo

from service.core.local_db import LocalDb

TOLERANCE_SECONDS = 120.0
BACKWARD = "backward"
FORWARD = "forward"


def utcnow() -> datetime:
    return datetime.now(UTC)


class TrustedClock:
    def __init__(
        self,
        db: LocalDb,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], datetime] = utcnow,
        tz: tzinfo | None = None,
        tolerance: float = TOLERANCE_SECONDS,
    ) -> None:
        self._db = db
        self._monotonic = monotonic
        self._wall = wall
        self._tz = tz
        self._tolerance = tolerance
        self._anchor = wall()
        self._anchor_mono = monotonic()
        self._online = False
        self._forward = False

    def _set_anchor(self, at: datetime) -> None:
        self._anchor = at.astimezone(UTC)
        self._anchor_mono = self._monotonic()

    def load(self) -> None:
        wall = self._wall()
        saved = self._db.load_last_trusted()
        self._set_anchor(wall if saved is None else max(wall, saved))

    def save(self) -> None:
        self._db.save_last_trusted(self.now())

    def now(self) -> datetime:
        return self._anchor + timedelta(seconds=self._monotonic() - self._anchor_mono)

    def local_now(self) -> datetime:
        return self.now().astimezone(self._tz)

    def online(self, server_time: datetime) -> None:
        self._set_anchor(server_time)
        self._online = True
        self._forward = (self._wall() - self._anchor).total_seconds() > self._tolerance

    def offline(self) -> None:
        self._online = False

    def check(self) -> str | None:
        drift = (self._wall() - self.now()).total_seconds()
        if drift < -self._tolerance:
            return BACKWARD
        if drift > self._tolerance and not self._online:
            self._set_anchor(self._wall())
            return None
        return FORWARD if self._forward else None
