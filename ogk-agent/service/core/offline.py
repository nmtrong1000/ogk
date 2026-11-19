"""Bounded fail-closed: under the limit the signed cached policies apply; from the limit on, the default policy
applies until the next successful heartbeat. The sync module and the development tools share this object,
so a simulated outage goes through the same switch as a real one.
Methods are synchronous; async callers run them in a worker thread.
"""

import logging
from datetime import datetime

from service.core.bus import POLICY_MODE, Bus
from service.core.clock import SyncClock
from service.core.policy_store import PolicyStore

log = logging.getLogger("ogk.sync")

DAY_SECONDS = 86400


class OfflineGuard:
    def __init__(self, clock: SyncClock, store: PolicyStore, bus: Bus, limit_days: float) -> None:
        self.clock = clock
        self._store = store
        self._bus = bus
        self._limit = limit_days * DAY_SECONDS

    def start(self) -> str:
        self.clock.load()
        return self.check()

    def online(self, server_time: datetime) -> None:
        self.clock.mark_online(server_time)
        self._apply(False)

    def offline(self) -> str:
        self.clock.tick()
        return self.check()

    def simulate(self, days: float) -> str:
        self.clock.simulate(days * DAY_SECONDS)
        return self.check()

    def check(self) -> str:
        self._apply(self.clock.offline_seconds() >= self._limit)
        return self._store.mode

    def _apply(self, expired: bool) -> None:
        if not self._store.set_expired(expired):
            return
        if expired:
            log.warning(
                "no successful heartbeat for %.1f days; applying the default policy",
                self.clock.offline_seconds() / DAY_SECONDS,
            )
        else:
            log.info("server reachable again; applying signed policies")
        self._bus.publish(POLICY_MODE, self._store.mode)
