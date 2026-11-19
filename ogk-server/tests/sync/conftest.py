import json
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.core.db import get_sessionmaker
from tests.enrollment.conftest import bearer, enroll_device
from tests.family.conftest import create_child
from tests.policy.conftest import agent, assign, device_accounts, other_parent

__all__ = ["agent", "other_parent"]

VECTORS = json.loads((Path(__file__).resolve().parents[3] / "docs" / "test_vectors.json").read_text(encoding="utf-8"))
EVENT_VECTORS = VECTORS["events"]


async def mapped_device(parent: httpx.AsyncClient, agent: httpx.AsyncClient, name: str = "PC") -> tuple[dict, dict]:
    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent, name=name)
    account = (await device_accounts(parent, tokens["device_id"]))[0]
    await assign(parent, tokens["device_id"], account["id"], child["id"])
    return tokens, child


def status(enabled: bool = True, reason: str | None = None) -> dict:
    return {
        "uptime": 10.5,
        "enforcement": {"enabled": enabled, "reason": reason, "since": "2026-11-19T08:00:00Z"},
        "policy_mode": "cached",
    }


def heartbeat_body(versions: dict | None = None, alerts: list | None = None, **status_kw) -> dict:
    return {
        "status": status(**status_kw),
        "quota_used": {},
        "policy_versions": versions or {},
        "alerts": alerts or [],
    }


async def send_heartbeat(agent: httpx.AsyncClient, token: str, body: dict) -> httpx.Response:
    return await agent.post("/api/device/heartbeat", json=body, headers=bearer(token))


def event(device_id: int, child_id: int, **overrides) -> dict:
    base = dict(EVENT_VECTORS["valid"][0]["event"])
    base.update(device_id=device_id, child_id=child_id)
    base.update(overrides)
    return base


async def post_events(
    agent: httpx.AsyncClient, token: str, events: list, key: str | None = "batch-1"
) -> httpx.Response:
    headers = bearer(token)
    if key is not None:
        headers["Idempotency-Key"] = key
    return await agent.post("/api/device/events", json={"events": events}, headers=headers)


async def count(model) -> int:
    async with get_sessionmaker()() as db:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()
