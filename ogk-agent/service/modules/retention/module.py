"""CHILD_PURGED is published before the DB delete so screen time drops its in-memory counters first; otherwise
its next periodic save would write the wiped usage back.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from service.core.agent import ModuleContext
from service.core.bus import CHILD_PURGED, Bus
from service.core.local_db import LocalDb
from service.core.request_state import RequestState

RETENTION_DAYS = 90
PURGE_INTERVAL_SECONDS = 24 * 60 * 60
PURGE_COMMANDS = ("purge_child",)

log = logging.getLogger("ogk.retention")


def utcnow() -> datetime:
    return datetime.now(UTC)


class RetentionModule:
    def __init__(
        self,
        db: LocalDb,
        bus: Bus,
        now: Callable[[], datetime] = utcnow,
        local_now: Callable[[], datetime] | None = None,
        requests: RequestState | None = None,
        interval: float = PURGE_INTERVAL_SECONDS,
    ) -> None:
        self._db = db
        self._bus = bus
        self._now = now
        self._local_now = local_now or (lambda: now().astimezone())
        self._requests = requests
        self._interval = interval

    async def purge_expired(self) -> dict[str, int]:
        cutoff = self._now() - timedelta(days=RETENTION_DAYS)
        cutoff_day = (self._local_now().date() - timedelta(days=RETENTION_DAYS)).isoformat()
        counts = await asyncio.to_thread(self._db.purge_before, cutoff, cutoff_day)
        log.info("retention purge removed %s", counts)
        return counts

    async def execute_command(self, command: dict[str, Any]) -> None:
        child_id = command["child_id"]
        if not isinstance(child_id, int) or isinstance(child_id, bool):
            raise ValueError("purge_child needs an integer child_id")
        self._bus.publish(CHILD_PURGED, child_id)
        if self._requests is not None:
            self._requests.forget_child(child_id)
        counts = await asyncio.to_thread(self._db.purge_child, child_id)
        log.info("purged local data of child %s: %s", child_id, counts)

    async def run(self) -> None:
        while True:
            try:
                await self.purge_expired()
            except Exception:
                log.exception("retention purge failed")
            await asyncio.sleep(self._interval)


def create(context: ModuleContext) -> RetentionModule:
    clock = context.clock
    module = RetentionModule(
        context.db,
        context.bus,
        now=utcnow if clock is None else clock.now,
        local_now=None if clock is None else clock.local_now,
        requests=context.request_state,
    )
    if context.commands is not None:
        context.commands.register(PURGE_COMMANDS, module.execute_command)
    return module
