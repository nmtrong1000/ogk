from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str


class AdminAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    failed_attempts: int
    locked_until: datetime | None
