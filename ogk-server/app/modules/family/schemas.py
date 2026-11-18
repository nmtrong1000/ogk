from datetime import datetime

from pydantic import BaseModel, ConfigDict

# Kiểu thô; giới hạn giá trị do service kiểm tra để lỗi trả về mã chuỗi (invalid_name, invalid_birth_year).


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
