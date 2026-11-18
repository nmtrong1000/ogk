import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.enrollment.models import DeviceToken
from tests.conftest import csrf_headers
from tests.enrollment.conftest import SECRET, bearer, enroll_device

pytestmark = pytest.mark.anyio


async def refresh(agent, tokens: dict, secret: str = SECRET, refresh_token: str | None = None):
    return await agent.post(
        "/api/device/token/refresh",
        json={
            "device_id": tokens["device_id"],
            "refresh_token": refresh_token or tokens["refresh_token"],
            "device_secret": secret,
        },
    )


async def me(agent, token: str):
    return await agent.get("/api/device/me", headers=bearer(token))


async def test_missing_or_unknown_token(agent):
    assert (await agent.get("/api/device/me")).json() == {"detail": "invalid_token"}
    assert (await me(agent, "nope")).json() == {"detail": "invalid_token"}


async def test_refresh_token_is_not_an_access_token(parent, agent):
    tokens = await enroll_device(parent, agent)
    assert (await me(agent, tokens["refresh_token"])).status_code == 401


async def test_access_token_expires_after_15_minutes(parent, agent, clock):
    tokens = await enroll_device(parent, agent)
    clock.advance(minutes=14, seconds=59)
    assert (await me(agent, tokens["access_token"])).status_code == 200
    clock.advance(seconds=1)
    response = await me(agent, tokens["access_token"])
    assert response.status_code == 401
    assert response.json() == {"detail": "token_expired"}


async def test_refresh_after_expiry(parent, agent, clock):
    tokens = await enroll_device(parent, agent)
    clock.advance(minutes=16)
    response = await refresh(agent, tokens)
    assert response.status_code == 200
    new = response.json()
    assert new["device_id"] == tokens["device_id"]
    assert new["access_token"] != tokens["access_token"]
    assert new["refresh_token"] != tokens["refresh_token"]
    assert (await me(agent, new["access_token"])).status_code == 200


async def test_refresh_revokes_old_access_token(parent, agent):
    tokens = await enroll_device(parent, agent)
    assert (await refresh(agent, tokens)).status_code == 200
    assert (await me(agent, tokens["access_token"])).json() == {"detail": "invalid_token"}


async def test_refresh_needs_device_secret(parent, agent):
    tokens = await enroll_device(parent, agent)
    response = await refresh(agent, tokens, secret="x" * 43)
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_refresh"}


async def test_refresh_token_of_other_device_is_rejected(parent, agent):
    first = await enroll_device(parent, agent)
    second = await enroll_device(parent, agent)
    response = await refresh(agent, first, refresh_token=second["refresh_token"])
    assert response.json() == {"detail": "invalid_refresh"}


async def test_reused_refresh_token_revokes_everything(parent, agent):
    tokens = await enroll_device(parent, agent)
    new = (await refresh(agent, tokens)).json()
    response = await refresh(agent, tokens)
    assert response.json() == {"detail": "invalid_refresh"}
    assert (await me(agent, new["access_token"])).status_code == 401
    assert (await refresh(agent, new)).json() == {"detail": "invalid_refresh"}


async def test_expired_refresh_token(parent, agent, clock):
    tokens = await enroll_device(parent, agent)
    clock.advance(days=30)
    assert (await refresh(agent, tokens)).json() == {"detail": "invalid_refresh"}


async def test_removed_device_cannot_call_api(parent, agent):
    tokens = await enroll_device(parent, agent)
    response = await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert response.status_code == 204
    response = await me(agent, tokens["access_token"])
    assert response.status_code == 401
    assert response.json() == {"detail": "device_revoked"}
    assert (await refresh(agent, tokens)).json() == {"detail": "device_revoked"}
    async with get_sessionmaker()() as db:
        rows = list((await db.execute(select(DeviceToken))).scalars())
    assert rows and all(r.revoked_at is not None for r in rows)


async def test_removed_device_is_hidden(parent, agent):
    tokens = await enroll_device(parent, agent)
    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert (await parent.get("/api/devices")).json() == []
    response = await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert response.status_code == 404


async def test_other_parent_cannot_remove_device(parent, other_parent, agent):
    tokens = await enroll_device(parent, agent)
    response = await other_parent.delete(
        f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(other_parent)
    )
    assert response.status_code == 404
    assert (await me(agent, tokens["access_token"])).status_code == 200


async def test_last_seen_is_updated(parent, agent):
    tokens = await enroll_device(parent, agent)
    assert (await parent.get("/api/devices")).json()[0]["last_seen_at"] is None
    await me(agent, tokens["access_token"])
    assert (await parent.get("/api/devices")).json()[0]["last_seen_at"] is not None
