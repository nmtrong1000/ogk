"""Device alerts are state, not events: the heartbeat sends the alerts active right now and the server closes
the ones that disappear, so a source must clear its alert once the condition is gone.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Alert:
    type: str
    detail: str | None
    since: datetime


class AlertBoard:
    def __init__(self) -> None:
        self._alerts: dict[str, Alert] = {}

    def raise_(self, type_: str, detail: str | None, at: datetime) -> None:
        held = self._alerts.get(type_)
        self._alerts[type_] = Alert(type_, detail, at if held is None else held.since)

    def clear(self, type_: str) -> None:
        self._alerts.pop(type_, None)

    def active(self) -> list[Alert]:
        return list(self._alerts.values())
