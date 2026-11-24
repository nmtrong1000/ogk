import sqlite3

import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.sync.models import DailyUsage
from tests.policy.test_migration import alembic
from tests.reports.conftest import frozen, two_children_device
from tests.sync.conftest import heartbeat_body, send_heartbeat

__all__ = ["frozen"]

pytestmark = pytest.mark.anyio


async def stored() -> list[tuple[int, str, int]]:
    async with get_sessionmaker()() as db:
        rows = await db.execute(select(DailyUsage.child_id, DailyUsage.day, DailyUsage.seconds))
        return sorted((child_id, day.isoformat(), seconds) for child_id, day, seconds in rows)


async def beat(agent, token: str, usage: list[dict]):
    return await send_heartbeat(agent, token, {**heartbeat_body(), "usage_days": usage})


async def test_usage_days_are_upserted(parent, agent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    token = tokens["access_token"]
    await beat(agent, token, [{"child_id": an["id"], "day": "2026-11-18", "seconds": 100}])
    await beat(
        agent,
        token,
        [
            {"child_id": an["id"], "day": "2026-11-18", "seconds": 250},
            {"child_id": an["id"], "day": "2026-11-19", "seconds": 30},
        ],
    )
    assert await stored() == [(an["id"], "2026-11-18", 250), (an["id"], "2026-11-19", 30)]


async def test_foreign_child_and_out_of_range_days_are_ignored(parent, agent, other_parent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    stranger = (await other_parent.get("/api/children")).json()
    usage = [
        {"child_id": an["id"], "day": "2026-08-20", "seconds": 1},
        {"child_id": an["id"], "day": "2026-11-21", "seconds": 1},
        {"child_id": 999999, "day": "2026-11-19", "seconds": 1},
        {"child_id": an["id"], "day": "2026-11-20", "seconds": 5},
    ]
    response = await beat(agent, tokens["access_token"], usage)
    assert response.status_code == 200
    assert stranger == []
    assert await stored() == [(an["id"], "2026-11-20", 5)]


async def test_invalid_usage_seconds_is_rejected(parent, agent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    response = await beat(agent, tokens["access_token"], [{"child_id": an["id"], "day": "2026-11-19", "seconds": -1}])
    assert response.status_code == 422


async def test_heartbeat_without_usage_days_still_works(parent, agent, frozen):
    tokens, _, _ = await two_children_device(parent, agent)
    assert (await send_heartbeat(agent, tokens["access_token"], heartbeat_body())).status_code == 200
    assert await stored() == []


def test_migration_0014_creates_and_drops_report_tables(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    alembic("upgrade", "head")
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"daily_usage", "child_view_codes", "child_view_sessions"} <= tables
    assert "ix_events_child_id_ts" in {r[1] for r in conn.execute("PRAGMA index_list(events)")}
    usage_columns = {r[1] for r in conn.execute("PRAGMA table_info(daily_usage)")}
    assert usage_columns == {"id", "device_id", "child_id", "day", "seconds", "updated_at"}
    alembic("downgrade", "0013")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not tables & {"daily_usage", "child_view_codes", "child_view_sessions"}
    assert "ix_events_child_id_ts" not in {r[1] for r in conn.execute("PRAGMA index_list(events)")}
