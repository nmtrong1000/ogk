import pytest

from tests.audit.conftest import audit_page
from tests.conftest import csrf_headers, make_client
from tests.enrollment.conftest import enroll_device
from tests.family.conftest import create_child

pytestmark = pytest.mark.anyio


@pytest.fixture
async def agent(app):
    async with make_client(app) as c:
        yield c


async def test_enroll_assign_remove_each_log_one_entry(parent, agent):
    me = (await parent.get("/api/auth/me")).json()
    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    page = await audit_page(parent)
    assert page["total"] == 2
    entry = page["items"][0]
    assert (entry["action"], entry["target_type"], entry["target_id"]) == ("create", "device", tokens["device_id"])
    assert entry["actor_id"] == me["id"]
    assert entry["new_value"] == {"name": "PC phòng khách"}

    account = (await parent.get("/api/devices")).json()[0]["accounts"][0]
    path = f"/api/devices/{tokens['device_id']}/accounts/{account['id']}"
    await parent.put(path, json={"child_id": child["id"]}, headers=await csrf_headers(parent))
    page = await audit_page(parent)
    assert page["total"] == 3
    entry = page["items"][0]
    assert (entry["action"], entry["target_type"], entry["target_id"]) == ("update", "windows_account", account["id"])
    assert (entry["old_value"], entry["new_value"]) == ({"child_id": None}, {"child_id": child["id"]})

    await parent.put(path, json={"child_id": child["id"]}, headers=await csrf_headers(parent))
    assert (await audit_page(parent))["total"] == 3

    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    page = await audit_page(parent)
    assert page["total"] == 4
    entry = page["items"][0]
    assert (entry["action"], entry["target_type"], entry["target_id"]) == ("delete", "device", tokens["device_id"])
    assert entry["old_value"] == {"name": "PC phòng khách"}


async def test_failed_enroll_logs_nothing(parent, agent):
    await agent.post(
        "/api/enroll",
        json={"code": "0000-0000", "fingerprint": "f" * 64, "device_secret": "s" * 43, "name": "x", "accounts": []},
    )
    assert (await audit_page(parent))["total"] == 0
