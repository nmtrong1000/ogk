import pytest
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.db import get_engine, get_owned, get_sessionmaker, select_owned

pytestmark = pytest.mark.anyio


async def test_anonymous_gets_401_on_admin_api(client):
    response = await client.get("/api/admin/accounts")
    assert response.status_code == 401


async def test_parent_gets_403_on_admin_api(parent):
    response = await parent.get("/api/admin/accounts")
    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


async def test_admin_can_use_admin_api(admin):
    assert (await admin.get("/api/admin/accounts")).status_code == 200


class _TestBase(DeclarativeBase):
    pass


class _Owner(_TestBase):
    __tablename__ = "test_owners"
    id: Mapped[int] = mapped_column(primary_key=True)


class _Thing(_TestBase):
    __tablename__ = "test_things"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("test_owners.id"))


async def test_owned_queries_filter_by_owner(app):
    async with get_engine().begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)
    async with get_sessionmaker()() as db:
        db.add_all([_Owner(id=1), _Owner(id=2), _Thing(id=10, owner_id=1), _Thing(id=20, owner_id=2)])
        await db.commit()

        assert (await get_owned(db, _Thing, 10, owner_id=1)).id == 10
        assert await get_owned(db, _Thing, 20, owner_id=1) is None
        ids = list((await db.execute(select_owned(_Thing, 2).with_only_columns(_Thing.id))).scalars())
        assert ids == [20]
        assert len(list((await db.execute(select(_Thing))).scalars())) == 2
