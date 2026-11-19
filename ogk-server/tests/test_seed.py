from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app import cli
from app.core.db import get_sessionmaker
from app.modules.audit.models import AuditLog
from app.modules.sync.models import DeviceAlert, Event
from app.seed import ADMIN_EMAIL, PARENT1_EMAIL, PARENT2_EMAIL, seed, window
from tests.conftest import login

pytestmark = pytest.mark.anyio

PASSWORD = "mat-khau-seed-1"
NOW = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)


async def run_seed(pairing_code: bool = False):
    async with get_sessionmaker()() as db:
        return await seed(db, PASSWORD, NOW, pairing_code)


async def count(model) -> int:
    async with get_sessionmaker()() as db:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()


def test_window_marks_half_hour_slots():
    day = window("16:00", "21:30")
    assert (len(day), day.index("1"), day.count("1")) == (48, 32, 11)


async def test_seed_creates_accounts_children_and_policies(app, client):
    report = await run_seed()
    assert report.created
    assert report.accounts == [ADMIN_EMAIL, PARENT1_EMAIL, PARENT2_EMAIL]
    assert report.children == {PARENT1_EMAIL: ["An", "Bình"], PARENT2_EMAIL: ["Chi", "Dũng"]}
    assert (await login(client, PARENT1_EMAIL, PASSWORD)).status_code == 200
    children = {c["name"]: c for c in (await client.get("/api/children")).json()}
    assert set(children) == {"An", "Bình"}
    policy = (await client.get(f"/api/children/{children['An']['id']}/policy")).json()
    assert (policy["weekday_quota_minutes"], policy["weekend_quota_minutes"]) == (120, 180)
    assert policy["weekly_schedule"][0] == window("16:00", "21:00")
    assert policy["weekly_schedule"][6] == window("08:00", "21:00")
    versions = (await client.get(f"/api/children/{children['An']['id']}/policy/versions")).json()
    assert len(versions) >= 2
    assert await count(AuditLog) > 0


async def test_sample_device_has_assigned_accounts_events_and_alerts(app, client):
    report = await run_seed()
    await login(client, PARENT1_EMAIL, PASSWORD)
    (device,) = (await client.get("/api/devices")).json()
    assert device["name"] == report.devices[0]
    assigned = {a["username"]: a["child_id"] for a in device["accounts"]}
    assert assigned["bo"] is None
    assert assigned["an"] is not None and assigned["binh"] is not None
    alerts = (await client.get("/api/alerts")).json()
    states = {(a["type"], a["resolved_at"] is None) for a in alerts}
    assert states == {("clock_tampered", True), ("enforcement_disabled", False)}
    assert report.events == await count(Event) > 0
    assert await count(DeviceAlert) == 2


async def test_second_parent_is_isolated(app, client):
    await run_seed()
    await login(client, PARENT2_EMAIL, PASSWORD)
    assert {c["name"] for c in (await client.get("/api/children")).json()} == {"Chi", "Dũng"}
    assert (await client.get("/api/devices")).json() == []


async def test_admin_can_log_in(app, client):
    await run_seed()
    response = await login(client, ADMIN_EMAIL, PASSWORD)
    assert response.status_code == 200
    assert (await client.get("/api/admin/accounts")).status_code == 200


async def test_running_again_creates_nothing(app):
    await run_seed()
    before = (await count(Event), await count(AuditLog))
    report = await run_seed()
    assert not report.created
    assert (await count(Event), await count(AuditLog)) == before


async def test_pairing_code_on_request(app):
    await run_seed()
    report = await run_seed(pairing_code=True)
    assert report.pairing_code is not None and len(report.pairing_code) == 9


def test_cli_refuses_without_password(settings_env, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OGK_SEED_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["seed-dev"]) == 1
    assert "OGK_SEED_PASSWORD" in capsys.readouterr().err
