import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.policy.models import Policy
from tests.audit.conftest import audit_page
from tests.conftest import csrf_headers
from tests.family.conftest import create_child
from tests.policy.conftest import set_quota

pytestmark = pytest.mark.anyio


async def test_get_creates_default_policy(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.get(f"/api/children/{child['id']}/policy")
    assert response.status_code == 200
    body = response.json()
    assert (body["child_id"], body["policy_version"], body["daily_quota_minutes"]) == (child["id"], 1, 120)


async def test_update_bumps_version_and_logs_once(parent):
    child = (await create_child(parent, "An")).json()
    before = (await audit_page(parent))["total"]
    response = await set_quota(parent, child["id"], 90)
    assert response.status_code == 200
    assert (response.json()["policy_version"], response.json()["daily_quota_minutes"]) == (2, 90)
    page = await audit_page(parent)
    assert page["total"] == before + 1
    entry = page["items"][0]
    assert (entry["action"], entry["target_type"], entry["target_id"]) == ("update", "policy", child["id"])
    assert entry["old_value"] == {"daily_quota_minutes": 120, "policy_version": 1}
    assert entry["new_value"] == {"daily_quota_minutes": 90, "policy_version": 2}
    assert (await set_quota(parent, child["id"], 30)).json()["policy_version"] == 3


async def test_same_value_keeps_version_and_logs_nothing(parent):
    child = (await create_child(parent, "An")).json()
    before = (await audit_page(parent))["total"]
    response = await set_quota(parent, child["id"], 120)
    assert response.json()["policy_version"] == 1
    assert (await audit_page(parent))["total"] == before


@pytest.mark.parametrize("minutes", [-1, 1441])
async def test_out_of_range_rejected(parent, minutes):
    child = (await create_child(parent, "An")).json()
    response = await set_quota(parent, child["id"], minutes)
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_quota"
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["policy_version"] == 1


async def test_other_parent_gets_not_found(parent, other_parent):
    child = (await create_child(parent, "An")).json()
    assert (await other_parent.get(f"/api/children/{child['id']}/policy")).status_code == 404
    response = await set_quota(other_parent, child["id"], 10)
    assert response.status_code == 404
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["daily_quota_minutes"] == 120


async def test_requires_csrf(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.patch(f"/api/children/{child['id']}/policy", json={"daily_quota_minutes": 10})
    assert response.status_code == 403
    assert response.json()["detail"] == "csrf_failed"


async def test_requires_login(client):
    assert (await client.get("/api/children/1/policy")).status_code == 401


async def test_admin_forbidden(admin):
    assert (await admin.get("/api/children/1/policy")).status_code == 403


async def test_deleting_child_removes_policy(parent):
    child = (await create_child(parent, "An")).json()
    await set_quota(parent, child["id"], 10)
    await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))
    async with get_sessionmaker()() as db:
        assert (await db.execute(select(Policy))).scalars().all() == []
