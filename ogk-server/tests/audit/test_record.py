import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.db import get_sessionmaker
from app.modules.audit import service
from app.modules.audit.models import AppendOnlyError, AuditLog
from app.modules.auth import service as auth_service

pytestmark = pytest.mark.anyio


async def _actor(db) -> service.Actor:
    account = await auth_service.create_account(db, "p@example.com", "dung-mat-khau-1")
    return service.Actor(account_id=account.id, ip="203.0.113.5")


async def test_record_writes_all_fields(app):
    async with get_sessionmaker()() as db:
        actor = await _actor(db)
        service.record(db, actor, "update", "child", 7, {"name": "An"}, {"name": "An Nhiên"})
        await db.commit()
        entry = (await db.execute(select(AuditLog))).scalar_one()
    assert entry.actor_id == actor.account_id
    assert entry.ip == "203.0.113.5"
    assert entry.at.tzinfo is not None
    assert (entry.action, entry.target_type, entry.target_id) == ("update", "child", 7)
    assert json.loads(entry.old_value) == {"name": "An"}
    assert json.loads(entry.new_value) == {"name": "An Nhiên"}


async def test_values_encrypted_at_rest(app):
    async with get_sessionmaker()() as db:
        service.record(db, await _actor(db), "create", "child", 1, None, {"name": "Bé Bí Mật"})
        await db.commit()
        raw = (await db.execute(text("SELECT old_value, new_value FROM audit_logs"))).one()
    assert raw.old_value is None
    assert "Bí Mật".encode() not in raw.new_value


async def test_record_rejects_unknown_action(app):
    async with get_sessionmaker()() as db:
        with pytest.raises(ValueError):
            service.record(db, await _actor(db), "truncate", "child", 1, None, None)


async def test_db_check_rejects_unknown_action(app):
    async with get_sessionmaker()() as db:
        actor = await _actor(db)
        await db.commit()
        with pytest.raises(IntegrityError):
            await db.execute(
                text(
                    "INSERT INTO audit_logs (actor_id, at, ip, action, target_type, target_id) "
                    "VALUES (:a, '2026-01-01', '::1', 'truncate', 'child', 1)"
                ),
                {"a": actor.account_id},
            )


async def _one_entry(db) -> AuditLog:
    service.record(db, await _actor(db), "create", "child", 1, None, {"name": "An"})
    await db.commit()
    return (await db.execute(select(AuditLog))).scalar_one()


async def test_orm_update_blocked(app):
    async with get_sessionmaker()() as db:
        entry = await _one_entry(db)
        entry.ip = "10.0.0.1"
        with pytest.raises(AppendOnlyError):
            await db.flush()


async def test_orm_delete_blocked(app):
    async with get_sessionmaker()() as db:
        entry = await _one_entry(db)
        await db.delete(entry)
        with pytest.raises(AppendOnlyError):
            await db.flush()


@pytest.mark.parametrize("sql", ["UPDATE audit_logs SET ip = '10.0.0.1'", "DELETE FROM audit_logs"])
async def test_sql_update_delete_blocked_by_trigger(app, sql):
    async with get_sessionmaker()() as db:
        await _one_entry(db)
        with pytest.raises(IntegrityError, match="append-only"):
            await db.execute(text(sql))
        await db.rollback()
        assert len((await db.execute(select(AuditLog))).scalars().all()) == 1
