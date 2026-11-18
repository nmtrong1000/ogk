import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.enrollment.models import ConsentRecord, PairingCode
from app.modules.family.models import Device
from tests.conftest import csrf_headers
from tests.enrollment.conftest import ACCOUNTS, SECRET, bearer, create_code, enroll, enroll_device

pytestmark = pytest.mark.anyio


async def test_enroll_returns_device_and_tokens(parent, agent):
    tokens = await enroll_device(parent, agent)
    assert set(tokens) == {"device_id", "access_token", "access_expires_at", "refresh_token", "refresh_expires_at"}
    assert tokens["access_token"] != tokens["refresh_token"]
    response = await agent.get("/api/device/me", headers=bearer(tokens["access_token"]))
    assert response.status_code == 200
    assert response.json() == {"id": tokens["device_id"], "name": "PC phòng khách"}


async def test_enrolled_device_shows_on_dashboard(parent, agent):
    tokens = await enroll_device(parent, agent)
    devices = (await parent.get("/api/devices")).json()
    assert [d["id"] for d in devices] == [tokens["device_id"]]
    accounts = devices[0]["accounts"]
    assert [(a["sid"], a["username"], a["child_id"]) for a in accounts] == [
        (a["sid"], a["username"], None) for a in ACCOUNTS
    ]


async def test_only_hashes_are_stored(parent, agent):
    tokens = await enroll_device(parent, agent)
    async with get_sessionmaker()() as db:
        device = await db.get(Device, tokens["device_id"])
        assert SECRET not in device.secret_hash
        assert len(device.secret_hash) == 64
        assert device.fingerprint_hash != "f" * 64
        codes = list((await db.execute(select(PairingCode))).scalars())
        assert all(len(c.code_hash) == 64 for c in codes)


async def test_duplicate_sids_are_merged(parent, agent):
    tokens = await enroll_device(parent, agent, accounts=ACCOUNTS + ACCOUNTS[:1])
    devices = (await parent.get("/api/devices")).json()
    assert devices[0]["id"] == tokens["device_id"]
    assert len(devices[0]["accounts"]) == 2


async def test_long_name_is_truncated(parent, agent):
    await enroll_device(parent, agent, name="x" * 200)
    assert len((await parent.get("/api/devices")).json()[0]["name"]) == 64


async def test_enroll_needs_no_csrf(parent, agent):
    code = (await create_code(parent)).json()["code"]
    assert "ogk_csrf" not in agent.cookies
    assert (await enroll(agent, code)).status_code == 201


async def test_short_secret_is_rejected(parent, agent):
    code = (await create_code(parent)).json()["code"]
    assert (await enroll(agent, code, device_secret="short")).status_code == 422


async def test_consent_record_after_enroll(parent, agent):
    me = (await parent.get("/api/auth/me")).json()
    tokens = await enroll_device(parent, agent)
    async with get_sessionmaker()() as db:
        records = list((await db.execute(select(ConsentRecord))).scalars())
        code = (await db.execute(select(PairingCode))).scalar_one()
    assert len(records) == 1
    record = records[0]
    assert record.account_id == me["id"]
    assert record.device_id == tokens["device_id"]
    assert record.ip == "127.0.0.1"
    assert record.consented_at == code.created_at
    assert record.consent_version


async def test_consent_record_per_enroll(parent, agent):
    await enroll_device(parent, agent)
    await enroll_device(parent, agent)
    async with get_sessionmaker()() as db:
        assert len(list((await db.execute(select(ConsentRecord))).scalars())) == 2


async def test_device_belongs_to_code_owner(parent, other_parent, agent):
    await enroll_device(parent, agent)
    assert (await other_parent.get("/api/devices")).json() == []


async def test_parent_routes_still_need_csrf(parent):
    response = await parent.put("/api/devices/1/accounts/1", json={"child_id": None})
    assert response.status_code == 403
    response = await parent.delete("/api/devices/1")
    assert response.status_code == 403
    assert (await parent.delete("/api/devices/1", headers=await csrf_headers(parent))).status_code == 404
