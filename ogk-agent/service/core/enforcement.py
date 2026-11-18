import datetime
import logging
from typing import Any

log = logging.getLogger("ogk.enforcement")


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class Enforcement:
    def __init__(self) -> None:
        self.enabled = True
        self.reason: str | None = None
        self.since = _now()

    def disable(self, reason: str) -> None:
        if not self.enabled and self.reason == reason:
            return
        self.enabled = False
        self.reason = reason
        self.since = _now()
        log.error("enforcement disabled: %s", reason)

    def enable(self) -> None:
        if self.enabled:
            return
        log.info("enforcement enabled again (was disabled: %s)", self.reason)
        self.enabled = True
        self.reason = None
        self.since = _now()

    def snapshot(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "reason": self.reason, "since": self.since}
