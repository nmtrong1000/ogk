"""Events are validated by the service from the raw body so every error carries the string code invalid_event."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from app.modules.sync.models import MAX_ALERT_DETAIL

AlertType = Literal["enforcement_disabled", "clock_tampered"]


class EnforcementIn(BaseModel):
    enabled: bool
    reason: str | None = Field(default=None, max_length=MAX_ALERT_DETAIL)
    since: AwareDatetime | None = None


class StatusIn(BaseModel):
    uptime: float = Field(ge=0)
    enforcement: EnforcementIn
    policy_mode: Literal["cached", "default"]


class AlertIn(BaseModel):
    type: AlertType
    detail: str | None = Field(default=None, max_length=MAX_ALERT_DETAIL)
    ts: AwareDatetime


class HeartbeatIn(BaseModel):
    status: StatusIn
    quota_used: dict[int, int] = Field(default_factory=dict)
    policy_versions: dict[int, int] = Field(default_factory=dict)
    alerts: list[AlertIn] = Field(default_factory=list, max_length=8)


class HeartbeatOut(BaseModel):
    policy_versions: dict[str, int]
    commands: list[dict]
    requests: list[dict] = Field(default_factory=list)
    server_time: str


class EventsOut(BaseModel):
    accepted: int
    duplicate: bool


class AlertOut(BaseModel):
    id: int
    device_id: int
    device_name: str
    type: str
    detail: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
