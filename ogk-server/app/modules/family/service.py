from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_owned, select_owned, utcnow
from app.core.errors import AppError
from app.modules.family.models import Child

MAX_NAME_LENGTH = 64
MIN_BIRTH_YEAR = 2000


def now() -> datetime:
    """Đồng hồ của module; test thay hàm này để giả lập thời gian."""
    return utcnow()


def validate_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise AppError(422, "invalid_name")
    return name


def validate_birth_year(birth_year: int) -> int:
    if not MIN_BIRTH_YEAR <= birth_year <= now().year:
        raise AppError(422, "invalid_birth_year")
    return birth_year


async def list_children(db: AsyncSession, owner_id: int) -> list[Child]:
    children = list((await db.execute(select_owned(Child, owner_id))).scalars())
    # Tên đã mã hóa trong DB nên không ORDER BY được; sắp sau khi giải mã.
    return sorted(children, key=lambda c: (c.name.casefold(), c.id))


async def get_child_for_owner(db: AsyncSession, child_id: int, owner_id: int) -> Child:
    """Trẻ của đúng phụ huynh; của người khác hoặc không tồn tại đều trả 404."""
    child = await get_owned(db, Child, child_id, owner_id)
    if child is None:
        raise AppError(404, "not_found")
    return child


async def create_child(db: AsyncSession, owner_id: int, name: str, birth_year: int) -> Child:
    at = now()
    child = Child(
        owner_id=owner_id,
        name=validate_name(name),
        birth_year=validate_birth_year(birth_year),
        created_at=at,
        updated_at=at,
    )
    db.add(child)
    await db.commit()
    return child


async def update_child(
    db: AsyncSession, child_id: int, owner_id: int, name: str | None = None, birth_year: int | None = None
) -> Child:
    child = await get_child_for_owner(db, child_id, owner_id)
    if name is not None:
        child.name = validate_name(name)
    if birth_year is not None:
        child.birth_year = validate_birth_year(birth_year)
    child.updated_at = now()
    await db.commit()
    return child


async def delete_child(db: AsyncSession, child_id: int, owner_id: int) -> None:
    """Xóa trẻ; tài khoản Windows đang gán cho trẻ được bỏ gán (ON DELETE SET NULL)."""
    child = await get_child_for_owner(db, child_id, owner_id)
    await db.delete(child)
    await db.commit()
