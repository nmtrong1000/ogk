"""Raw input types; the service validates value ranges
so errors return string codes (invalid_name, invalid_birth_year).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChildCreate(BaseModel):
    name: str
    birth_year: int


class ChildUpdate(BaseModel):
    name: str | None = None
    birth_year: int | None = None


class ChildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    birth_year: int
    created_at: datetime
    updated_at: datetime


class WindowsAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sid: str
    username: str
    child_id: int | None


class DeviceOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    last_seen_at: datetime | None
    accounts: list[WindowsAccountOut]


class AssignIn(BaseModel):
    child_id: int | None
