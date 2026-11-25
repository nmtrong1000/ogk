import json

import pytest

from app.core import signing
from app.modules.policy.models import APP_GROUPS
from app.modules.webfilter.catalog_data import catalog_rows
from tests.conftest import csrf_headers
from tests.enrollment.conftest import bearer, enroll_device
from tests.family.conftest import create_child
from tests.policy.conftest import DEFAULT_SCHEDULE, assign, device_accounts, set_quota

pytestmark = pytest.mark.anyio


async def fetch(agent, token: str):
    return await agent.get("/api/device/policy", headers=bearer(token))


async def test_returns_signed_policies_of_mapped_children(parent, agent):
    an = (await create_child(parent, "An")).json()
    binh = (await create_child(parent, "Bình")).json()
    tokens = await enroll_device(parent, agent)
    first, second = await device_accounts(parent, tokens["device_id"])
    await assign(parent, tokens["device_id"], first["id"], an["id"])
    await assign(parent, tokens["device_id"], second["id"], binh["id"])

    response = await fetch(agent, tokens["access_token"])
    assert response.status_code == 200
    items = response.json()["policies"]
    assert [item["policy"]["child_id"] for item in items] == [an["id"], binh["id"]]
    public_key = signing.get_signing_key().public_key()
    assert [item["policy"]["accounts"] for item in items] == [[first["sid"]], [second["sid"]]]
    for item in items:
        assert item["policy"]["policy_version"] == 1
        assert item["policy"]["set_by"] == "parent@example.com"
        assert item["policy"]["rules"] == {
            "weekday_quota_minutes": 120,
            "weekend_quota_minutes": 120,
            "weekly_schedule": DEFAULT_SCHEDULE,
            "app_rules": [],
            "app_groups": json.loads(APP_GROUPS),
            "web_allowlist": [],
            "web_blocklist": [],
            "blocked_categories": ["adult", "social"],
            "category_domains": {
                category: [domain for domain, group in catalog_rows() if group == category]
                for category in {group for _domain, group in catalog_rows()}
            },
        }
        assert item["key_id"] == signing.key_id(public_key)
        assert signing.verify(public_key, item["policy"], item["signature"])


async def test_child_on_two_accounts_listed_once(parent, agent):
    an = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    for account in await device_accounts(parent, tokens["device_id"]):
        await assign(parent, tokens["device_id"], account["id"], an["id"])
    items = (await fetch(agent, tokens["access_token"])).json()["policies"]
    assert [item["policy"]["child_id"] for item in items] == [an["id"]]
    sids = sorted(a["sid"] for a in await device_accounts(parent, tokens["device_id"]))
    assert items[0]["policy"]["accounts"] == sids


async def test_unmapped_child_and_other_device_excluded(parent, agent):
    an = (await create_child(parent, "An")).json()
    await create_child(parent, "Bình")
    pc1 = await enroll_device(parent, agent, name="PC1")
    pc2 = await enroll_device(parent, agent, name="PC2")
    account = (await device_accounts(parent, pc1["device_id"]))[0]
    await assign(parent, pc1["device_id"], account["id"], an["id"])
    assert (await fetch(agent, pc2["access_token"])).json() == {"policies": []}
    assert len((await fetch(agent, pc1["access_token"])).json()["policies"]) == 1


async def test_agent_sees_new_version_after_edit(parent, agent):
    an = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device_accounts(parent, tokens["device_id"]))[0]
    await assign(parent, tokens["device_id"], account["id"], an["id"])
    await set_quota(parent, an["id"], 45)
    (item,) = (await fetch(agent, tokens["access_token"])).json()["policies"]
    assert item["policy"]["policy_version"] == 2
    assert item["policy"]["rules"]["weekday_quota_minutes"] == 45


async def test_same_version_signs_identically(parent, agent):
    an = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device_accounts(parent, tokens["device_id"]))[0]
    await assign(parent, tokens["device_id"], account["id"], an["id"])
    first = (await fetch(agent, tokens["access_token"])).json()
    assert (await fetch(agent, tokens["access_token"])).json() == first


async def test_requires_device_token(parent, agent):
    assert (await agent.get("/api/device/policy")).json()["detail"] == "invalid_token"
    assert (await fetch(agent, "wrong")).status_code == 401
    assert (await parent.get("/api/device/policy")).status_code == 401


async def test_revoked_device_rejected(parent, agent):
    tokens = await enroll_device(parent, agent)
    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    response = await fetch(agent, tokens["access_token"])
    assert response.status_code == 401
    assert response.json()["detail"] == "device_revoked"


async def test_assigning_account_bumps_existing_policy(parent, agent):
    an = (await create_child(parent, "An")).json()
    binh = (await create_child(parent, "Bình")).json()
    tokens = await enroll_device(parent, agent)
    first, second = await device_accounts(parent, tokens["device_id"])
    await assign(parent, tokens["device_id"], first["id"], an["id"])
    (item,) = (await fetch(agent, tokens["access_token"])).json()["policies"]
    assert item["policy"]["policy_version"] == 1

    await assign(parent, tokens["device_id"], second["id"], an["id"])
    (item,) = (await fetch(agent, tokens["access_token"])).json()["policies"]
    assert item["policy"]["policy_version"] == 2
    assert item["policy"]["accounts"] == sorted([first["sid"], second["sid"]])

    await parent.get(f"/api/children/{binh['id']}/policy")
    await assign(parent, tokens["device_id"], second["id"], binh["id"])
    items = (await fetch(agent, tokens["access_token"])).json()["policies"]
    assert [(i["policy"]["child_id"], i["policy"]["policy_version"]) for i in items] == [(an["id"], 3), (binh["id"], 2)]
    assert items[0]["policy"]["accounts"] == [first["sid"]]


async def test_unassigning_bumps_and_removes_child(parent, agent):
    an = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device_accounts(parent, tokens["device_id"]))[0]
    await assign(parent, tokens["device_id"], account["id"], an["id"])
    await fetch(agent, tokens["access_token"])
    await assign(parent, tokens["device_id"], account["id"], None)
    assert (await fetch(agent, tokens["access_token"])).json() == {"policies": []}
    assert (await parent.get(f"/api/children/{an['id']}/policy")).json()["policy_version"] == 2
