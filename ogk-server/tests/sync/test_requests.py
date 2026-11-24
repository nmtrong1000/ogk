import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.sync.models import ChildRequest, ParentCommand
from tests.conftest import csrf_headers
from tests.sync.conftest import heartbeat_body, mapped_device, send_heartbeat

pytestmark = pytest.mark.anyio


async def submit(agent, token, child_id, kind, domain=None):
    body = {"child_id": child_id, "type": kind}
    if domain is not None:
        body["domain"] = domain
    return await agent.post("/api/device/requests", json=body, headers={"Authorization": f"Bearer {token}"})


async def test_add_time_request_is_listed_audited_and_delivered(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    created = await submit(agent, tokens["access_token"], child["id"], "add_time")
    assert created.status_code == 201
    request_id = created.json()["id"]
    items = await parent.get("/api/requests?status=pending")
    assert items.json()[0]["id"] == request_id
    decided = await parent.post(
        f"/api/requests/{request_id}/decision",
        json={"approve": True, "message": "Thêm 15 phút nhé."},
        headers=await csrf_headers(parent),
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    heartbeat = await send_heartbeat(agent, tokens["access_token"], heartbeat_body())
    assert heartbeat.json()["requests"][0]["message"] == "Thêm 15 phút nhé."
    assert heartbeat.json()["commands"][0]["type"] == "add_time"
    async with get_sessionmaker()() as db:
        command = await db.scalar(select(ParentCommand))
        saved = await db.get(ChildRequest, request_id)
    assert command.type == "add_time"
    assert command.minutes == 15
    assert saved.status == "approved"


async def test_blocked_domain_approval_updates_policy(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    created = await submit(agent, tokens["access_token"], child["id"], "blocked_domain", "School.Example.")
    assert created.status_code == 201
    result = await parent.post(
        f"/api/requests/{created.json()['id']}/decision",
        json={"approve": True, "message": "Đã mở trang."},
        headers=await csrf_headers(parent),
    )
    assert result.status_code == 200
    policy = await parent.get(f"/api/children/{child['id']}/policy")
    assert "school.example" in policy.json()["web_allowlist"]


async def test_request_requires_assigned_child_and_decision_is_once(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    wrong = await submit(agent, tokens["access_token"], child["id"] + 100, "add_time")
    assert wrong.status_code == 404
    created = await submit(agent, tokens["access_token"], child["id"], "add_time")
    request_id = created.json()["id"]
    body = {"approve": False}
    path = f"/api/requests/{request_id}/decision"
    first = await parent.post(path, json=body, headers=await csrf_headers(parent))
    second = await parent.post(path, json=body, headers=await csrf_headers(parent))
    assert first.status_code == 200
    assert second.status_code == 409


async def test_invalid_blocked_domain_is_rejected(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    response = await submit(agent, tokens["access_token"], child["id"], "blocked_domain", "https://bad/path")
    assert response.status_code == 422


async def test_other_parent_cannot_list_or_decide_request(parent, agent, other_parent):
    tokens, child = await mapped_device(parent, agent)
    created = await submit(agent, tokens["access_token"], child["id"], "add_time")
    listed = await other_parent.get("/api/requests")
    decision = await other_parent.post(
        f"/api/requests/{created.json()['id']}/decision",
        json={"approve": True},
        headers=await csrf_headers(other_parent),
    )
    assert listed.json() == []
    assert decision.status_code == 404
