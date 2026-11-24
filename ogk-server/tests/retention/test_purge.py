import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.auth.models import Account
from app.modules.retention import service as retention
from app.modules.sync.models import ChildRequest, DailyUsage, DeviceAlert, Event, EventBatch, ParentCommand
from tests.retention.conftest import NOW, seed_history
from tests.sync.conftest import count, mapped_device

pytestmark = pytest.mark.anyio

HISTORY = (Event, EventBatch, DeviceAlert, ChildRequest, ParentCommand, DailyUsage)


async def parent_id() -> int:
    async with get_sessionmaker()() as db:
        return (await db.execute(select(Account.id).where(Account.email == "parent@example.com"))).scalar_one()


async def test_purge_removes_only_records_older_than_90_days(parent, agent, monkeypatch):
    tokens, child = await mapped_device(parent, agent)
    actor_id = await parent_id()
    await seed_history(tokens["device_id"], child["id"], actor_id, 91, "old")
    await seed_history(tokens["device_id"], child["id"], actor_id, 89, "recent")
    monkeypatch.setattr(retention, "now", lambda: NOW)

    async with get_sessionmaker()() as db:
        counts = await retention.purge_expired(db)

    assert set(counts.values()) == {1}
    for model in HISTORY:
        assert await count(model) == 1, model.__tablename__
    async with get_sessionmaker()() as db:
        subjects = (await db.execute(select(Event.subject))).scalars().all()
    assert subjects == ["recent.exe"]


async def test_open_alert_is_kept_while_still_reported(parent, agent, monkeypatch):
    tokens, child = await mapped_device(parent, agent)
    await seed_history(tokens["device_id"], child["id"], await parent_id(), 91, "old")
    async with get_sessionmaker()() as db:
        alert = (await db.execute(select(DeviceAlert))).scalar_one()
        alert.resolved_at = None
        alert.last_seen_at = NOW
        await db.commit()
    monkeypatch.setattr(retention, "now", lambda: NOW)

    async with get_sessionmaker()() as db:
        await retention.purge_expired(db)

    assert await count(DeviceAlert) == 1
