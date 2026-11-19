"""Events are written to the local DB before any send, so an outage or a restart loses nothing.
A batch keeps the idempotency key it got before its first send until the server acknowledges it, so a retry
after a lost response is ignored by the server instead of counted twice. A 422 means the server will never
accept the batch; it is dropped so it does not block every later batch.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import httpx

from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.events import validate_event
from service.core.local_db import LocalDb
from service.core.server_client import ApiError

log = logging.getLogger("ogk.events")

BATCH_SIZE = 500


def new_key() -> str:
    return str(uuid.uuid4())


class EventQueue:
    def __init__(self, db: LocalDb, session: DeviceSession | None, batch_size: int = BATCH_SIZE) -> None:
        self._db = db
        self._session = session
        self._batch_size = batch_size
        self._lock = asyncio.Lock()

    async def enqueue(self, events: Iterable[Any]) -> int:
        clean = [validate_event(event) for event in events]
        payloads = [json.dumps(event, separators=(",", ":")) for event in clean]
        await asyncio.to_thread(self._db.add_events, payloads, datetime.now(UTC))
        return len(payloads)

    async def pending(self) -> int:
        return await asyncio.to_thread(self._db.pending_events)

    async def flush(self) -> int:
        if self._session is None:
            return 0
        async with self._lock:
            sent = 0
            while True:
                batch = await asyncio.to_thread(self._db.next_event_batch, self._batch_size, new_key)
                if batch is None:
                    return sent
                events = [json.loads(payload) for payload in batch.payloads]
                try:
                    result = await self._session.post_events(events, batch.key)
                except (NotEnrolled, DeviceRevoked, httpx.HTTPError) as exc:
                    log.info("events kept for retry (%d pending): %s", len(events), exc or type(exc).__name__)
                    return sent
                except ApiError as exc:
                    if exc.status != 422:
                        log.warning("events kept for retry: %s", exc)
                        return sent
                    log.error("server rejected event batch %s, dropping %d events: %s", batch.key, len(events), exc)
                else:
                    if result.get("duplicate"):
                        log.info("event batch %s was already stored by the server", batch.key)
                    sent += len(events)
                await asyncio.to_thread(self._db.delete_event_batch, batch.key)
