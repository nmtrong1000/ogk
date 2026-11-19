"""Raw input types; the service validates ranges so errors return the string codes invalid_quota and
invalid_schedule. Every PolicyUpdate field is optional because the dashboard saves quotas and the schedule
separately.
"""

from datetime import datetime

from pydantic import BaseModel


class PolicyUpdate(BaseModel):
    weekday_quota_minutes: int | None = None
    weekend_quota_minutes: int | None = None
    weekly_schedule: list[str] | None = None


class PolicyOut(BaseModel):
    child_id: int
    policy_version: int
    weekday_quota_minutes: int
    weekend_quota_minutes: int
    weekly_schedule: list[str]
    set_by: str | None
    updated_at: datetime


class PolicyVersionOut(BaseModel):
    policy_version: int
    weekday_quota_minutes: int
    weekend_quota_minutes: int
    weekly_schedule: list[str]
    set_by: str | None
    created_at: datetime


class SignedPolicyOut(BaseModel):
    policy: dict
    signature: str
    key_id: str


class DevicePoliciesOut(BaseModel):
    policies: list[SignedPolicyOut]
