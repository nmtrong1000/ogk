import pytest

from tests.conftest import csrf_headers, make_client
from tests.enrollment.conftest import enroll_device
from tests.family.conftest import create_child

pytestmark = pytest.mark.anyio


@pytest.fixture
async def agent(app):
    async with make_client(app) as c:
        yield c


async def assign(c, device_id: int, account_id: int, child_id: int | None):
    return await c.put(
        f"/api/devices/{device_id}/accounts/{account_id}", json={"child_id": child_id}, headers=await csrf_headers(c)
    )


async def device(c, device_id: int) -> dict:
    return next(d for d in (await c.get("/api/devices")).json() if d["id"] == device_id)


async def test_assign_account_to_child(parent, agent):
    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device(parent, tokens["device_id"]))["accounts"][0]
    response = await assign(parent, tokens["device_id"], account["id"], child["id"])
    assert response.status_code == 200
    assert response.json()["child_id"] == child["id"]
    assert (await device(parent, tokens["device_id"]))["accounts"][0]["child_id"] == child["id"]


async def test_unassign(parent, agent):
    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device(parent, tokens["device_id"]))["accounts"][0]
    await assign(parent, tokens["device_id"], account["id"], child["id"])
    assert (await assign(parent, tokens["device_id"], account["id"], None)).json()["child_id"] is None


async def test_two_children_share_one_device(parent, agent):
    an = (await create_child(parent, "An")).json()
    binh = (await create_child(parent, "Bình")).json()
    tokens = await enroll_device(parent, agent)
    first, second = (await device(parent, tokens["device_id"]))["accounts"]
    await assign(parent, tokens["device_id"], first["id"], an["id"])
    await assign(parent, tokens["device_id"], second["id"], binh["id"])
    for child in (an, binh):
        devices = (await parent.get(f"/api/children/{child['id']}/devices")).json()
        assert [d["id"] for d in devices] == [tokens["device_id"]]


async def test_one_child_on_two_devices(parent, agent):
    an = (await create_child(parent, "An")).json()
    pc1 = await enroll_device(parent, agent, name="PC1")
    pc2 = await enroll_device(parent, agent, name="PC2")
    for tokens in (pc1, pc2):
        account = (await device(parent, tokens["device_id"]))["accounts"][0]
        await assign(parent, tokens["device_id"], account["id"], an["id"])
    devices = (await parent.get(f"/api/children/{an['id']}/devices")).json()
    assert [d["name"] for d in devices] == ["PC1", "PC2"]


async def test_child_without_devices(parent):
    child = (await create_child(parent, "An")).json()
    assert (await parent.get(f"/api/children/{child['id']}/devices")).json() == []


async def test_removed_device_not_listed_for_child(parent, agent):
    an = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device(parent, tokens["device_id"]))["accounts"][0]
    await assign(parent, tokens["device_id"], account["id"], an["id"])
    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert (await parent.get(f"/api/children/{an['id']}/devices")).json() == []


async def test_cannot_assign_child_of_other_parent(parent, other_parent, agent):
    foreign = (await create_child(other_parent, "Lạ")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device(parent, tokens["device_id"]))["accounts"][0]
    response = await assign(parent, tokens["device_id"], account["id"], foreign["id"])
    assert response.status_code == 404
    assert response.json() == {"detail": "child_not_found"}


async def test_cannot_assign_on_other_parents_device(parent, other_parent, agent):
    own = (await create_child(other_parent, "Của tôi")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device(parent, tokens["device_id"]))["accounts"][0]
    response = await assign(other_parent, tokens["device_id"], account["id"], own["id"])
    assert response.status_code == 404
    assert response.json() == {"detail": "not_found"}


async def test_account_must_belong_to_device(parent, agent):
    child = (await create_child(parent, "An")).json()
    pc1 = await enroll_device(parent, agent)
    pc2 = await enroll_device(parent, agent)
    account = (await device(parent, pc2["device_id"]))["accounts"][0]
    assert (await assign(parent, pc1["device_id"], account["id"], child["id"])).status_code == 404


async def test_other_parent_cannot_list_child_devices(parent, other_parent):
    child = (await create_child(parent, "An")).json()
    assert (await other_parent.get(f"/api/children/{child['id']}/devices")).status_code == 404


async def test_deleting_child_unassigns(parent, agent):
    child = (await create_child(parent, "An")).json()
    tokens = await enroll_device(parent, agent)
    account = (await device(parent, tokens["device_id"]))["accounts"][0]
    await assign(parent, tokens["device_id"], account["id"], child["id"])
    await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))
    assert (await device(parent, tokens["device_id"]))["accounts"][0]["child_id"] is None


async def test_admin_cannot_list_devices(admin):
    assert (await admin.get("/api/devices")).status_code == 403
