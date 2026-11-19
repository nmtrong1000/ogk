import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.policy.models import Policy, PolicyVersion
from tests.audit.conftest import audit_page
from tests.conftest import csrf_headers
from tests.family.conftest import create_child
from tests.policy.conftest import DEFAULT_DAY, DEFAULT_SCHEDULE, patch_policy, set_quota

pytestmark = pytest.mark.anyio

CLOSED_SUNDAY = [DEFAULT_DAY] * 6 + ["0" * 48]


async def test_get_creates_default_policy(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.get(f"/api/children/{child['id']}/policy")
    assert response.status_code == 200
    body = response.json()
    assert body["child_id"] == child["id"]
    assert body["policy_version"] == 1
    assert (body["weekday_quota_minutes"], body["weekend_quota_minutes"]) == (120, 120)
    assert body["weekly_schedule"] == DEFAULT_SCHEDULE
    assert body["set_by"] == "parent@example.com"


async def test_update_bumps_version_and_logs_once(parent):
    child = (await create_child(parent, "An")).json()
    before = (await audit_page(parent))["total"]
    response = await patch_policy(parent, child["id"], weekday_quota_minutes=90, weekend_quota_minutes=150)
    assert response.status_code == 200
    body = response.json()
    assert (body["policy_version"], body["weekday_quota_minutes"], body["weekend_quota_minutes"]) == (2, 90, 150)
    page = await audit_page(parent)
    assert page["total"] == before + 1
    entry = page["items"][0]
    assert (entry["action"], entry["target_type"], entry["target_id"]) == ("update", "policy", child["id"])
    assert entry["old_value"] == {"weekday_quota_minutes": 120, "weekend_quota_minutes": 120, "policy_version": 1}
    assert entry["new_value"] == {"weekday_quota_minutes": 90, "weekend_quota_minutes": 150, "policy_version": 2}
    assert (await set_quota(parent, child["id"], 30)).json()["policy_version"] == 3


async def test_schedule_update_reads_back(parent):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], weekly_schedule=CLOSED_SUNDAY)
    assert response.status_code == 200
    body = (await parent.get(f"/api/children/{child['id']}/policy")).json()
    assert (body["policy_version"], body["weekly_schedule"]) == (2, CLOSED_SUNDAY)
    assert body["weekday_quota_minutes"] == 120
    entry = (await audit_page(parent))["items"][0]
    assert entry["new_value"] == {"weekly_schedule": "".join(CLOSED_SUNDAY), "policy_version": 2}


async def test_same_value_keeps_version_and_logs_nothing(parent):
    child = (await create_child(parent, "An")).json()
    before = (await audit_page(parent))["total"]
    response = await patch_policy(
        parent, child["id"], weekday_quota_minutes=120, weekend_quota_minutes=120, weekly_schedule=DEFAULT_SCHEDULE
    )
    assert response.json()["policy_version"] == 1
    assert (await patch_policy(parent, child["id"])).json()["policy_version"] == 1
    assert (await audit_page(parent))["total"] == before


@pytest.mark.parametrize("field", ["weekday_quota_minutes", "weekend_quota_minutes"])
@pytest.mark.parametrize("minutes", [-1, 1441])
async def test_out_of_range_rejected(parent, field, minutes):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], **{field: minutes})
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_quota"
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["policy_version"] == 1


@pytest.mark.parametrize(
    "schedule",
    [
        [DEFAULT_DAY] * 6,
        [DEFAULT_DAY] * 8,
        [DEFAULT_DAY[:-1]] + [DEFAULT_DAY] * 6,
        [DEFAULT_DAY[:-1] + "2"] + [DEFAULT_DAY] * 6,
        [DEFAULT_DAY[:-1] + " "] + [DEFAULT_DAY] * 6,
    ],
)
async def test_invalid_schedule_rejected(parent, schedule):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], weekly_schedule=schedule)
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_schedule"


async def test_invalid_field_rejects_whole_update(parent):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], weekday_quota_minutes=30, weekly_schedule=["1"])
    assert response.status_code == 422
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["weekday_quota_minutes"] == 120


async def test_other_parent_gets_not_found(parent, other_parent):
    child = (await create_child(parent, "An")).json()
    assert (await other_parent.get(f"/api/children/{child['id']}/policy")).status_code == 404
    assert (await other_parent.get(f"/api/children/{child['id']}/policy/versions")).status_code == 404
    response = await set_quota(other_parent, child["id"], 10)
    assert response.status_code == 404
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["weekday_quota_minutes"] == 120


async def test_requires_csrf(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.patch(f"/api/children/{child['id']}/policy", json={"weekday_quota_minutes": 10})
    assert response.status_code == 403
    assert response.json()["detail"] == "csrf_failed"


async def test_requires_login(client):
    assert (await client.get("/api/children/1/policy")).status_code == 401
    assert (await client.get("/api/children/1/policy/versions")).status_code == 401


async def test_admin_forbidden(admin):
    assert (await admin.get("/api/children/1/policy")).status_code == 403


async def test_deleting_child_removes_policy_and_history(parent):
    child = (await create_child(parent, "An")).json()
    await set_quota(parent, child["id"], 10)
    await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))
    async with get_sessionmaker()() as db:
        assert (await db.execute(select(Policy))).scalars().all() == []
        assert (await db.execute(select(PolicyVersion))).scalars().all() == []
