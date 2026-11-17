from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import DateTime, Select, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _set_sqlite_pragmas(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _ensure_db_dir(url: str) -> None:
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_engine(url: str) -> AsyncEngine:
    _ensure_db_dir(url)
    engine = create_async_engine(url)
    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


@lru_cache
def get_engine() -> AsyncEngine:
    return create_engine(get_settings().database_url)


@lru_cache
def get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def check_db() -> str:
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
        return (await conn.execute(text("PRAGMA journal_mode"))).scalar_one()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Lưu UTC không kèm múi giờ trong SQLite, đọc ra datetime có tzinfo=UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime phải có múi giờ")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, _dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


M = TypeVar("M")


def select_owned(model: type[M], owner_id: Any) -> Select[tuple[M]]:
    """SELECT luôn lọc theo chủ sở hữu. Model phải có cột owner_id."""
    return select(model).where(model.owner_id == owner_id)


async def get_owned(db: AsyncSession, model: type[M], obj_id: Any, owner_id: Any) -> M | None:
    """Lấy một đối tượng của đúng chủ sở hữu; của người khác thì trả None như không tồn tại."""
    stmt = select_owned(model, owner_id).where(model.id == obj_id)
    return (await db.execute(stmt)).scalar_one_or_none()
