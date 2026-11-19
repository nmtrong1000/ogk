import pytest

from app.modules.sync import service as sync_service
from tests.conftest import csrf_headers
from tests.enrollment.conftest import enroll_device
from tests.policy.conftest import set_quota
from tests.sync.conftest import heartbeat_body, mapped_device, send_heartbeat

pytestmark = pytest.mark.anyio

DISABLED = {"type": "enforcement_disabled", "detail": "tray_unavailable", "ts": "2026-11-19T08:00:00Z"}


async def test_returns_latest_versions_commands_and_server_time(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    response = await send_heartbeat(agent, tokens["access_token"], heartbeat_body({child["id"]: 1}))
    assert response.status_code == 200
    body = response.json()
    assert body["policy_versions"] == {str(child["id"]): 1}
    assert body["commands"] == []
    assert body["server_time"].endswith("Z")


async def test_version_mismatch_after_policy_edit(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    await send_heartbeat(agent, tokens["access_token"], heartbeat_body({child["id"]: 1}))
    await set_quota(parent, child["id"], 45)
    body = (await send_heartbeat(agent, tokens["access_token"], heartbeat_body({child["id"]: 1}))).json()
    assert body["policy_versions"] == {str(child["id"]): 2}


async def test_device_without_children_gets_empty_versions(parent, agent):
    tokens = await enroll_device(parent, agent)
    body = (await send_heartbeat(agent, tokens["access_token"], heartbeat_body())).json()
    assert body["policy_versions"] == {}


async def test_server_time_uses_server_clock(parent, agent, monkeypatch):
    tokens, _ = await mapped_device(parent, agent)
    at = sync_service.now().replace(year=2030, microsecond=0)
    monkeypatch.setattr(sync_service, "now", lambda: at)
    body = (await send_heartbeat(agent, tokens["access_token"], heartbeat_body())).json()
    assert body["server_time"] == at.strftime("%Y-%m-%dT%H:%M:%SZ")


async def test_alert_opens_updates_and_resolves(parent, agent):
    tokens, _ = await mapped_device(parent, agent)
    token = tokens["access_token"]
    await send_heartbeat(agent, token, heartbeat_body(alerts=[DISABLED], enabled=False, reason="tray_unavailable"))
    (opened,) = (await parent.get("/api/alerts")).json()
    assert opened["type"] == "enforcement_disabled"
    assert opened["detail"] == "tray_unavailable"
    assert opened["resolved_at"] is None

    await send_heartbeat(agent, token, heartbeat_body(alerts=[DISABLED, DISABLED]))
    (same,) = (await parent.get("/api/alerts")).json()
    assert same["id"] == opened["id"]
    assert same["last_seen_at"] >= opened["last_seen_at"]

    await send_heartbeat(agent, token, heartbeat_body())
    (resolved,) = (await parent.get("/api/alerts")).json()
    assert resolved["resolved_at"] is not None

    await send_heartbeat(agent, token, heartbeat_body(alerts=[DISABLED]))
    alerts = (await parent.get("/api/alerts")).json()
    assert len(alerts) == 2
    assert alerts[0]["resolved_at"] is None


async def test_rejects_unknown_alert_type(parent, agent):
    tokens, _ = await mapped_device(parent, agent)
    body = heartbeat_body(alerts=[{**DISABLED, "type": "app_start"}])
    assert (await send_heartbeat(agent, tokens["access_token"], body)).status_code == 422


async def test_requires_device_token(parent, agent):
    assert (await agent.post("/api/device/heartbeat", json=heartbeat_body())).json()["detail"] == "invalid_token"
    assert (await send_heartbeat(agent, "wrong", heartbeat_body())).status_code == 401


async def test_revoked_device_rejected(parent, agent):
    tokens, _ = await mapped_device(parent, agent)
    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    response = await send_heartbeat(agent, tokens["access_token"], heartbeat_body())
    assert response.json()["detail"] == "device_revoked"
