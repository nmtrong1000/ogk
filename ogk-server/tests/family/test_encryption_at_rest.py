"""Sensitive fields are ciphertext on disk. The engine is disposed first to flush the WAL for outside readers."""

import sqlite3

import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker, utcnow
from app.modules.family.models import Device, WindowsAccount
from tests.conftest import csrf_headers
from tests.family.conftest import birth_year, create_child

pytestmark = pytest.mark.anyio


def _raw_db() -> sqlite3.Connection:
    return sqlite3.connect(make_url(get_settings().database_url).database)


async def test_child_fields_unreadable_in_db_file(parent):
    year = birth_year(9)
    await create_child(parent, "Nguyễn Bình An", year)
    await get_engine().dispose()

    with _raw_db() as conn:
        name, stored_year = conn.execute("SELECT name, birth_year FROM children").fetchone()
        dump = "\n".join(conn.iterdump())
    assert isinstance(name, bytes) and isinstance(stored_year, bytes)
    assert "Nguyễn Bình An".encode() not in name
    assert str(year).encode() not in stored_year
    assert "Nguyễn Bình An" not in dump


async def test_windows_username_encrypted_and_unassigned_on_child_delete(parent):
    child = (await create_child(parent)).json()
    owner_id = (await parent.get("/api/auth/me")).json()["id"]
    async with get_sessionmaker()() as db:
        device = Device(owner_id=owner_id, name="PC phòng khách", created_at=utcnow())
        db.add(device)
        await db.flush()
        db.add(WindowsAccount(device_id=device.id, child_id=child["id"], sid="S-1-5-21-1-1001", username="be.an"))
        await db.commit()

    assert (await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))).status_code == 204
    await get_engine().dispose()
    with _raw_db() as conn:
        child_id, username = conn.execute("SELECT child_id, username FROM windows_accounts").fetchone()
    assert child_id is None
    assert b"be.an" not in username

