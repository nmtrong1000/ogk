import uuid

import pytest

from tests.audit.conftest import audit_page
from tests.family.conftest import create_child
from tests.policy.conftest import patch_policy

pytestmark = pytest.mark.anyio

DEFAULT_GROUPS = [
    {"id": "education", "name": "Học tập", "budget_minutes": None},
    {"id": "entertainment", "name": "Giải trí", "budget_minutes": None},
    {"id": "social", "name": "Mạng xã hội", "budget_minutes": None},
    {"id": "games", "name": "Trò chơi", "budget_minutes": None},
    {"id": "adult", "name": "Người lớn", "budget_minutes": None},
    {"id": "unclassified", "name": "Chưa phân loại", "budget_minutes": None},
]


async def test_default_groups_and_custom_groups_round_trip_with_audit(parent):
    child = (await create_child(parent, "An")).json()
    initial = (await parent.get(f"/api/children/{child['id']}/policy")).json()
    assert initial["app_groups"] == DEFAULT_GROUPS
    custom = {"id": f"custom_{uuid.uuid4()}", "name": "Vẽ", "budget_minutes": 60}
    groups = [{**group, "budget_minutes": 45} if group["id"] == "games" else group for group in DEFAULT_GROUPS]
    groups.append(custom)
    before = (await audit_page(parent))["total"]
    response = await patch_policy(parent, child["id"], app_groups=groups)
    assert response.status_code == 200
    assert custom in response.json()["app_groups"]
    assert response.json()["policy_version"] == 2
    entry = (await audit_page(parent))["items"][0]
    assert entry["action"] == "update"
    assert entry["new_value"]["app_groups"] == response.json()["app_groups"]
    assert (await audit_page(parent))["total"] == before + 1


async def test_app_rule_references_group_and_signed_policy_includes_groups(parent, agent):
    from tests.enrollment.conftest import bearer, enroll_device
    from tests.policy.conftest import assign, device_accounts

    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device_accounts(parent, tokens["device_id"]))[0]
    await assign(parent, tokens["device_id"], account["id"], child["id"])
    game = {**DEFAULT_GROUPS[3], "budget_minutes": 45}
    groups = sorted(
        [game if group["id"] == "games" else group for group in DEFAULT_GROUPS], key=lambda group: group["id"]
    )
    await patch_policy(parent, child["id"], app_groups=groups)
    await patch_policy(parent, child["id"], app_rules=[{"name": "game.exe", "action": "block", "group_id": "games"}])
    result = (await agent.get("/api/device/policy", headers=bearer(tokens["access_token"]))).json()
    signed_rules = result["policies"][0]["policy"]["rules"]
    assert signed_rules["app_groups"] == groups
    assert signed_rules["app_rules"][0]["group_id"] == "games"


@pytest.mark.parametrize(
    "change",
    [
        lambda groups: groups[:-1],
        lambda groups: [*groups, {"id": "custom_bad", "name": "Bad", "budget_minutes": 5}],
        lambda groups: [{**groups[3], "budget_minutes": 1441}, *groups[:3], *groups[4:]],
        lambda groups: [{**groups[3], "budget_minutes": True}, *groups[:3], *groups[4:]],
    ],
)
async def test_invalid_groups_rejected_without_changing_policy(parent, change):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], app_groups=change(DEFAULT_GROUPS))
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_app_groups"
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["policy_version"] == 1


async def test_group_cannot_be_removed_while_app_is_assigned(parent):
    child = (await create_child(parent, "An")).json()
    custom = {"id": f"custom_{uuid.uuid4()}", "name": "Vẽ", "budget_minutes": 5}
    await patch_policy(parent, child["id"], app_groups=[*DEFAULT_GROUPS, custom])
    await patch_policy(
        parent, child["id"], app_rules=[{"name": "game.exe", "action": "block", "group_id": custom["id"]}]
    )
    response = await patch_policy(parent, child["id"], app_groups=DEFAULT_GROUPS)
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_app_rules"
