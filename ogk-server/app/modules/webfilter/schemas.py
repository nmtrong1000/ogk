from datetime import datetime

from pydantic import BaseModel


class CatalogEntry(BaseModel):
    domain: str
    category: str
    updated_at: datetime


class CatalogChange(BaseModel):
    category: str | None
