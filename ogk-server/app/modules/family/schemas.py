"""Raw input types; the service validates value ranges so errors return string codes (invalid_name, invalid_birth_year)."""

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
