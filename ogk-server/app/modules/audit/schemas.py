from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: int
    at: datetime
    actor_id: int
    actor_email: str | None
    ip: str
    action: str
    target_type: str
    target_id: int
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None


class AuditPageOut(BaseModel):
    items: list[AuditEntryOut]
    total: int
    page: int
    size: int
