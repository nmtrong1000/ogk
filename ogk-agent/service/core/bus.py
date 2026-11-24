"""Handlers run synchronously in the event loop thread; publishers on other threads must hop onto the loop
first (call_soon_threadsafe) before calling publish.
SERVER_TIME carries the server_time of a successful heartbeat, or None when a heartbeat fails.
CHILD_PURGED carries the child_id whose local data was just wiped; holders of in-memory copies drop them.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

log = logging.getLogger("ogk.bus")

SESSION = "session"
TRAY_HEARTBEAT = "tray_heartbeat"
POLICY = "policy"
POLICY_STALE = "policy_stale"
POLICY_MODE = "policy_mode"
SERVER_TIME = "server_time"
CHILD_PURGED = "child_purged"

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
    sid: str = ""


@dataclass(frozen=True)
class TrayPing:
    pid: int
    idle_seconds: float | None = None
    foreground: str | None = None


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
