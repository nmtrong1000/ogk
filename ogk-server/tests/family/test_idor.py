import pytest

from tests.conftest import csrf_headers
from tests.family.conftest import create_child

pytestmark = pytest.mark.anyio


async def test_other_parent_cannot_read_update_or_delete(parent, other_parent):
    child = (await create_child(parent, "Con của A")).json()
    url = f"/api/children/{child['id']}"

    assert (await other_parent.get(url)).status_code == 404
    response = await other_parent.patch(url, json={"name": "Bị sửa"}, headers=await csrf_headers(other_parent))
    assert response.status_code == 404
    assert response.json() == {"detail": "not_found"}
    assert (await other_parent.delete(url, headers=await csrf_headers(other_parent))).status_code == 404

    assert (await parent.get(url)).json() == child


async def test_lists_are_separated(parent, other_parent):
    await create_child(parent, "Con của A")
    await create_child(other_parent, "Con của B")
    assert [c["name"] for c in (await parent.get("/api/children")).json()] == ["Con của A"]
    assert [c["name"] for c in (await other_parent.get("/api/children")).json()] == ["Con của B"]


async def test_not_owned_looks_like_missing(parent, other_parent):
    child = (await create_child(parent)).json()
    owned_by_other = await other_parent.get(f"/api/children/{child['id']}")
    missing = await other_parent.get("/api/children/9999")
    assert owned_by_other.status_code == missing.status_code == 404
    assert owned_by_other.json() == missing.json()
