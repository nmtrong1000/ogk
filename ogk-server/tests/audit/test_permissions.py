import pytest

from tests.audit.conftest import audit_page
from tests.conftest import csrf_headers
from tests.family.conftest import create_child

pytestmark = pytest.mark.anyio


async def test_requires_login(client):
    assert (await client.get("/api/audit")).status_code == 401


async def test_parent_sees_only_own_entries(parent, other_parent):
    await create_child(parent, "Của A")
    await create_child(other_parent, "Của B")
    await create_child(other_parent, "Của B 2")

    mine = await audit_page(parent)
    assert mine["total"] == 1
    assert mine["items"][0]["new_value"]["name"] == "Của A"
    assert {e["actor_email"] for e in mine["items"]} == {"parent@example.com"}

    theirs = await audit_page(other_parent)
    assert theirs["total"] == 2
    assert {e["actor_email"] for e in theirs["items"]} == {"other@example.com"}


async def test_admin_sees_all_without_values(parent, other_parent, admin):
    await create_child(parent, "Của A")
    await create_child(other_parent, "Của B")
    page = await audit_page(admin)
    assert page["total"] == 2
    assert {e["actor_email"] for e in page["items"]} == {"parent@example.com", "other@example.com"}
    for entry in page["items"]:
        assert entry["old_value"] is None and entry["new_value"] is None
        assert entry["ip"] and entry["action"] == "create" and entry["target_type"] == "child"


async def test_pagination(parent):
    for i in range(5):
        await create_child(parent, f"Con {i}")
    first = await audit_page(parent, page=1, size=2)
    second = await audit_page(parent, page=2, size=2)
    last = await audit_page(parent, page=3, size=2)
    assert first["total"] == 5 and (first["page"], first["size"]) == (1, 2)
    assert [e["new_value"]["name"] for e in first["items"]] == ["Con 4", "Con 3"]
    assert [e["new_value"]["name"] for e in second["items"]] == ["Con 2", "Con 1"]
    assert [e["new_value"]["name"] for e in last["items"]] == ["Con 0"]
    assert (await audit_page(parent, page=4, size=2))["items"] == []


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}])
async def test_invalid_page_params(parent, params):
    assert (await parent.get("/api/audit", params=params)).status_code == 422


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("path", ["/api/audit", "/api/audit/1"])
async def test_no_write_api(parent, method, path):
    await create_child(parent, "An")
    response = await parent.request(method, path, json={}, headers=await csrf_headers(parent))
    assert response.status_code in (404, 405)
    assert (await audit_page(parent))["total"] == 1


async def test_no_write_route_registered(app):
    methods = {
        method
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/audit")
        for method in getattr(route, "methods", set())
    }
    assert methods <= {"GET", "HEAD"}
