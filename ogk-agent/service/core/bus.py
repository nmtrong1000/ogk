"""Handlers run synchronously in the event loop thread; publishers on other threads must hop onto the loop
first (call_soon_threadsafe) before calling publish.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

log = logging.getLogger("ogk.bus")

SESSION = "session"
TRAY_HEARTBEAT = "tray_heartbeat"

SessionKind = Literal["logon", "logoff", "lock", "unlock"]
SESSION_KINDS: tuple[SessionKind, ...] = ("logon", "logoff", "lock", "unlock")


@dataclass(frozen=True)
class SessionEvent:
    kind: SessionKind
    session_id: int


@dataclass(frozen=True)
class SessionInfo:
    session_id: int
    username: str


Handler = Callable[[Any], None]


class Bus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    def publish(self, topic: str, payload: Any = None) -> None:
        for handler in list(self._handlers[topic]):
            try:
                handler(payload)
            except Exception:
                log.exception("handler for %s failed", topic)
