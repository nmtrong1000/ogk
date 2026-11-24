from datetime import UTC, datetime

import httpx
import pytest

from app.modules.reports import service as reports_service
from app.modules.sync import service as sync_service
from tests.enrollment.conftest import bearer, enroll_device
from tests.family.conftest import create_child
from tests.policy.conftest import agent, assign, device_accounts, other_parent

__all__ = ["agent", "other_parent"]

NOW = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)
CODE = "c" * 43


@pytest.fixture
def frozen(monkeypatch):
    clock = {"at": NOW}
    monkeypatch.setattr(reports_service, "now", lambda: clock["at"])
    monkeypatch.setattr(sync_service, "now", lambda: clock["at"])
    return clock


async def two_children_device(parent: httpx.AsyncClient, agent: httpx.AsyncClient) -> tuple[dict, dict, dict]:
    an = (await create_child(parent, "An")).json()
    binh = (await create_child(parent, "Bình")).json()
    tokens = await enroll_device(parent, agent)
    accounts = await device_accounts(parent, tokens["device_id"])
    await assign(parent, tokens["device_id"], accounts[0]["id"], an["id"])
    await assign(parent, tokens["device_id"], accounts[1]["id"], binh["id"])
    return tokens, an, binh


async def register_code(agent: httpx.AsyncClient, token: str, child_id: int, code: str = CODE) -> httpx.Response:
    return await agent.post(
        "/api/device/child-view-codes", json={"child_id": child_id, "code": code}, headers=bearer(token)
    )
