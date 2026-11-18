from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PairingCodeCreate(BaseModel):
    consent: bool


class PairingCodeOut(BaseModel):
    id: int
    code: str
    expires_at: datetime
    expires_in: int


class PairingCodeStatusOut(BaseModel):
    id: int
    status: Literal["pending", "used", "expired"]
    expires_at: datetime
    device_id: int | None


class EnrollAccountIn(BaseModel):
    sid: str = Field(min_length=1, max_length=184)
    username: str = Field(min_length=1, max_length=256)


class EnrollIn(BaseModel):
    code: str = Field(max_length=32)
    fingerprint: str = Field(min_length=16, max_length=128)
    device_secret: str = Field(min_length=32, max_length=128)
    name: str = Field(max_length=256)
    accounts: list[EnrollAccountIn] = Field(max_length=64)


class TokensOut(BaseModel):
    device_id: int
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


class RefreshIn(BaseModel):
    device_id: int
    refresh_token: str = Field(max_length=128)
    device_secret: str = Field(max_length=128)


class DeviceMeOut(BaseModel):
    id: int
    name: str
