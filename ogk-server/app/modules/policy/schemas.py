"""Raw input types; the service validates the range so the error returns the string code invalid_quota."""

from datetime import datetime

from pydantic import BaseModel


class PolicyUpdate(BaseModel):
    daily_quota_minutes: int


class PolicyOut(BaseModel):
    child_id: int
    policy_version: int
    daily_quota_minutes: int
    updated_at: datetime


class SignedPolicyOut(BaseModel):
    policy: dict
    signature: str
    key_id: str


class DevicePoliciesOut(BaseModel):
    policies: list[SignedPolicyOut]
