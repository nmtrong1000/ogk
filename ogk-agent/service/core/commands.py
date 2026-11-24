import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from service.core.local_db import LocalDb

CommandHandler = Callable[[dict[str, Any]], Awaitable[None]]
log = logging.getLogger("ogk.commands")


class CommandState:
    def __init__(self, db: LocalDb | None = None) -> None:
        self._db = db
        self._handlers: dict[str, CommandHandler] = {}
        self._processed: set[int] = set()
        self._lock = asyncio.Lock()

    def register(self, kinds: tuple[str, ...], handler: CommandHandler) -> None:
        for kind in kinds:
            self._handlers[kind] = handler

    async def process(self, command: dict[str, Any]) -> bool:
        command_id = command.get("id")
        if not isinstance(command_id, int) or isinstance(command_id, bool):
            return False
        async with self._lock:
            already_processed = command_id in self._processed
            if not already_processed and self._db is not None:
                already_processed = await asyncio.to_thread(self._db.has_command_receipt, command_id)
            if not already_processed:
                handler = self._handlers.get(command.get("type"))
                if handler is None:
                    log.error("parent command %s has no handler for type %r", command_id, command.get("type"))
                    return False
                try:
                    await handler(command)
                except Exception:
                    log.exception("parent command %s could not be applied", command_id)
                    return False
                self._processed.add(command_id)
                if self._db is not None:
                    await asyncio.to_thread(self._db.save_command_receipt, command_id, datetime.now(UTC))
            return True
