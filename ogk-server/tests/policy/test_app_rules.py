import pytest

from tests.audit.conftest import audit_page
from tests.enrollment.conftest import bearer, enroll_device
from tests.family.conftest import create_child
from tests.policy.conftest import assign, device_accounts, patch_policy

pytestmark = pytest.mark.anyio

SHA = "AB" * 32
NOTEPAD = {"name": "Notepad.EXE", "sha256": SHA, "action": "block"}
STORED_NOTEPAD = {"name": "notepad.exe", "sha256": SHA.lower(), "action": "block"}
GAME = {"name": "game.exe", "action": "block"}
STORED_GAME = {"name": "game.exe", "sha256": None, "action": "block"}


async def test_default_policy_has_no_app_rules(parent):
    child = (await create_child(parent, "An")).json()
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["app_rules"] == []


async def test_rules_are_normalized_sorted_and_read_back(parent):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], app_rules=[NOTEPAD, GAME])
    assert response.status_code == 200
    assert response.json()["policy_version"] == 2
    body = (await parent.get(f"/api/children/{child['id']}/policy")).json()
    assert body["app_rules"] == [STORED_GAME, STORED_NOTEPAD]
    versions = (await parent.get(f"/api/children/{child['id']}/policy/versions")).json()
    assert [v["app_rules"] for v in versions] == [[STORED_GAME, STORED_NOTEPAD], []]


async def test_update_logs_old_and_new_lists_once(parent):
    child = (await create_child(parent, "An")).json()
    await patch_policy(parent, child["id"], app_rules=[GAME])
    before = (await audit_page(parent))["total"]
    await patch_policy(parent, child["id"], app_rules=[NOTEPAD])
    page = await audit_page(parent)
    assert page["total"] == before + 1
    entry = page["items"][0]
    assert entry["old_value"] == {"app_rules": [STORED_GAME], "policy_version": 2}
    assert entry["new_value"] == {"app_rules": [STORED_NOTEPAD], "policy_version": 3}


async def test_reordered_or_recased_list_is_not_a_change(parent):
    child = (await create_child(parent, "An")).json()
    await patch_policy(parent, child["id"], app_rules=[NOTEPAD, GAME])
    before = (await audit_page(parent))["total"]
    response = await patch_policy(parent, child["id"], app_rules=[STORED_GAME, STORED_NOTEPAD])
    assert response.json()["policy_version"] == 2
    assert (await audit_page(parent))["total"] == before


async def test_empty_list_clears_rules(parent):
    child = (await create_child(parent, "An")).json()
    await patch_policy(parent, child["id"], app_rules=[GAME])
    response = await patch_policy(parent, child["id"], app_rules=[])
    assert (response.json()["policy_version"], response.json()["app_rules"]) == (3, [])


@pytest.mark.parametrize(
    "rule",
    [
        {"name": "", "action": "block"},
        {"name": "   ", "action": "block"},
        {"name": "x" * 256, "action": "block"},
        {"name": "C:\\games\\game.exe", "action": "block"},
        {"name": "bin/game", "action": "block"},
        {"name": "game.exe", "action": "deny"},
        {"name": "game.exe", "sha256": "abc", "action": "block"},
        {"name": "game.exe", "sha256": "g" * 64, "action": "block"},
    ],
)
async def test_invalid_rule_rejected(parent, rule):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(parent, child["id"], app_rules=[rule])
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_app_rules"
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["policy_version"] == 1


async def test_duplicate_pair_rejected(parent):
    child = (await create_child(parent, "An")).json()
    duplicate = {**GAME, "name": "GAME.exe", "action": "allow"}
    response = await patch_policy(parent, child["id"], app_rules=[GAME, duplicate])
    assert response.json()["detail"] == "invalid_app_rules"


async def test_same_name_with_different_hashes_allowed(parent):
    child = (await create_child(parent, "An")).json()
    rules = [GAME, {"name": "game.exe", "sha256": "0" * 64, "action": "allow"}]
    assert (await patch_policy(parent, child["id"], app_rules=rules)).status_code == 200


async def test_more_than_200_rules_rejected(parent):
    child = (await create_child(parent, "An")).json()
    rules = [{"name": f"app{i}.exe", "action": "block"} for i in range(201)]
    response = await patch_policy(parent, child["id"], app_rules=rules)
    assert response.json()["detail"] == "invalid_app_rules"
    assert (await patch_policy(parent, child["id"], app_rules=rules[:200])).status_code == 200


async def test_bad_field_rejects_whole_request(parent):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(
        parent, child["id"], weekday_quota_minutes=30, app_rules=[{"name": "x", "action": "no"}]
    )
    assert response.status_code == 422
    assert (await parent.get(f"/api/children/{child['id']}/policy")).json()["weekday_quota_minutes"] == 120


async def test_other_parents_child_not_found(parent, other_parent):
    child = (await create_child(parent, "An")).json()
    response = await patch_policy(other_parent, child["id"], app_rules=[GAME])
    assert response.status_code == 404


async def test_signed_device_policy_carries_rules(parent, agent):
    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device_accounts(parent, tokens["device_id"]))[0]
    await assign(parent, tokens["device_id"], account["id"], child["id"])
    await patch_policy(parent, child["id"], app_rules=[NOTEPAD])
    items = (await agent.get("/api/device/policy", headers=bearer(tokens["access_token"]))).json()["policies"]
    assert items[0]["policy"]["rules"]["app_rules"] == [STORED_NOTEPAD]
