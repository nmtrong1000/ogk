from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DayUsageOut(BaseModel):
    date: date
    seconds: int


class WeekUsageOut(BaseModel):
    week_start: date
    seconds: int


class AppUsageOut(BaseModel):
    name: str
    seconds: int


class DomainUsageOut(BaseModel):
    domain: str
    count: int


class BlockedOut(BaseModel):
    apps: int
    domains: int
    total: int


class ReportOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    child_id: int
    start: date = Field(alias="from")
    end: date = Field(alias="to")
    time_zone: str
    daily: list[DayUsageOut]
    weekly: list[WeekUsageOut]
    total_seconds: int
    top_apps: list[AppUsageOut]
    top_domains: list[DomainUsageOut]
    blocked: BlockedOut
    quota_today_seconds: int


class ChildRequestOut(BaseModel):
    id: int
    device_id: int
    child_id: int
    child_name: str | None
    type: str
    domain: str | None
    status: str
    message: str | None
    created_at: datetime
    decided_at: datetime | None


class ChildRequestPageOut(BaseModel):
    items: list[ChildRequestOut]
    total: int
    page: int
    size: int


class RuleChangeOut(BaseModel):
    id: int
    at: datetime
    changes: dict[str, dict[str, Any]]


class RuleLogPageOut(BaseModel):
    items: list[RuleChangeOut]
    total: int
    page: int
    size: int


class ChildProfileOut(BaseModel):
    name: str


class CodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_id: int = Field(strict=True)
    code: str = Field(max_length=128)


class CodeOut(BaseModel):
    expires_at: datetime


class SessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=128)
