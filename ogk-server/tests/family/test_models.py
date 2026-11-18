import pytest
from sqlalchemy import insert

from app.core.db import get_sessionmaker, utcnow
from app.modules.family.models import Device, WindowsAccount
from tests.family.conftest import create_child

pytestmark = pytest.mark.anyio


async def test_one_child_many_devices_and_shared_device(parent):
    owner_id = (await parent.get("/api/auth/me")).json()["id"]
    an = (await create_child(parent, "An")).json()["id"]
    binh = (await create_child(parent, "Bình")).json()["id"]
    async with get_sessionmaker()() as db:
        pc1 = Device(
            owner_id=owner_id, name="PC1", created_at=utcnow(), fingerprint_hash="0" * 64, secret_hash="0" * 64
        )
        pc2 = Device(
            owner_id=owner_id, name="PC2", created_at=utcnow(), fingerprint_hash="0" * 64, secret_hash="0" * 64
        )
        db.add_all([pc1, pc2])
        await db.flush()
        await db.execute(
            insert(WindowsAccount),
            [
                {"device_id": pc1.id, "child_id": an, "sid": "S-1", "username": "an"},
                {"device_id": pc2.id, "child_id": an, "sid": "S-1", "username": "an"},
                {"device_id": pc1.id, "child_id": binh, "sid": "S-2", "username": "binh"},
            ],
        )
        await db.commit()
        rows = (await db.execute(WindowsAccount.__table__.select())).all()
    assert {r.device_id for r in rows if r.child_id == an} == {pc1.id, pc2.id}
    assert {r.child_id for r in rows if r.device_id == pc1.id} == {an, binh}
