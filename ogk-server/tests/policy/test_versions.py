import pytest

from tests.family.conftest import create_child
from tests.policy.conftest import DEFAULT_SCHEDULE, patch_policy, set_quota

pytestmark = pytest.mark.anyio


async def versions(c, child_id: int) -> list[dict]:
    response = await c.get(f"/api/children/{child_id}/policy/versions")
    assert response.status_code == 200
    return response.json()


async def test_first_read_has_version_one(parent):
    child = (await create_child(parent, "An")).json()
    (first,) = await versions(parent, child["id"])
    assert first["policy_version"] == 1
    assert (first["weekday_quota_minutes"], first["weekly_schedule"]) == (120, DEFAULT_SCHEDULE)
    assert first["set_by"] == "parent@example.com"


async def test_each_change_adds_a_snapshot_newest_first(parent):
    child = (await create_child(parent, "An")).json()
    await set_quota(parent, child["id"], 60)
    await patch_policy(parent, child["id"], weekend_quota_minutes=200)
    await set_quota(parent, child["id"], 60)
    items = await versions(parent, child["id"])
    assert [v["policy_version"] for v in items] == [3, 2, 1]
    assert [(v["weekday_quota_minutes"], v["weekend_quota_minutes"]) for v in items] == [
        (60, 200),
        (60, 120),
        (120, 120),
    ]


async def test_history_snapshots_web_filter_rules(parent):
    child = (await create_child(parent, "An")).json()
    await patch_policy(
        parent,
        child["id"],
        web_allowlist=["school.edu.vn"],
        web_blocklist=["example.com"],
        blocked_categories=["adult"],
    )
    items = await versions(parent, child["id"])
    assert items[0]["web_allowlist"] == ["school.edu.vn"]
    assert items[0]["web_blocklist"] == ["example.com"]
    assert items[0]["blocked_categories"] == ["adult"]
    assert items[1]["web_allowlist"] == []
    assert items[1]["web_blocklist"] == []
    assert items[1]["blocked_categories"] == ["adult", "social"]


async def test_history_is_capped(parent):
    child = (await create_child(parent, "An")).json()
    for minutes in range(1, 56):
        await set_quota(parent, child["id"], minutes)
    items = await versions(parent, child["id"])
    assert len(items) == 50
    assert items[0]["policy_version"] == 56
