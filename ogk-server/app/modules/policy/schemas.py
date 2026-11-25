"""Raw input types; the service validates ranges so errors return the string codes invalid_quota,
invalid_schedule and invalid_app_rules. Every PolicyUpdate field is optional because the dashboard saves
quotas, the schedule and app rules separately.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AppRule(BaseModel):
    name: str
    sha256: str | None = None
    action: str
    group_id: str = "unclassified"


class AppGroup(BaseModel):
    id: str
    name: str
    budget_minutes: Any = None


class PolicyUpdate(BaseModel):
    weekday_quota_minutes: int | None = None
    weekend_quota_minutes: int | None = None
    weekly_schedule: list[str] | None = None
    app_rules: list[AppRule] | None = None
    app_groups: list[AppGroup] | None = None
    web_allowlist: list[str] | None = None
    web_blocklist: list[str] | None = None
    blocked_categories: list[str] | None = None


class PolicyOut(BaseModel):
    child_id: int
    policy_version: int
    weekday_quota_minutes: int
    weekend_quota_minutes: int
    weekly_schedule: list[str]
    app_rules: list[AppRule]
    app_groups: list[AppGroup]
    web_allowlist: list[str]
    web_blocklist: list[str]
    blocked_categories: list[str]
    set_by: str | None
    updated_at: datetime


class PolicyVersionOut(BaseModel):
    policy_version: int
    weekday_quota_minutes: int
    weekend_quota_minutes: int
    weekly_schedule: list[str]
    app_rules: list[AppRule]
    app_groups: list[AppGroup]
    web_allowlist: list[str]
    web_blocklist: list[str]
    blocked_categories: list[str]
    set_by: str | None
    created_at: datetime


class SignedPolicyOut(BaseModel):
    policy: dict
    signature: str
    key_id: str


class DevicePoliciesOut(BaseModel):
    policies: list[SignedPolicyOut]
