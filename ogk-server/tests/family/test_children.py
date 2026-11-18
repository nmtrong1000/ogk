import pytest

from tests.conftest import csrf_headers
from tests.family.conftest import birth_year, create_child

pytestmark = pytest.mark.anyio


async def test_create_and_get(parent):
    response = await create_child(parent, "  Bé An  ", birth_year(8))
    assert response.status_code == 201
    child = response.json()
    assert child["name"] == "Bé An"
    assert child["birth_year"] == birth_year(8)
    assert set(child) == {"id", "name", "birth_year", "created_at", "updated_at"}

    got = await parent.get(f"/api/children/{child['id']}")
    assert got.status_code == 200
    assert got.json() == child


async def test_list_many_sorted_by_name(parent):
    for name in ["Chi", "an", "Bình"]:
        assert (await create_child(parent, name)).status_code == 201
    response = await parent.get("/api/children")
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["an", "Bình", "Chi"]


async def test_update_partial(parent):
    child = (await create_child(parent, "An", birth_year(8))).json()
    response = await parent.patch(
        f"/api/children/{child['id']}", json={"name": "An Nhiên"}, headers=await csrf_headers(parent)
    )
    assert response.status_code == 200
    assert response.json()["name"] == "An Nhiên"
    assert response.json()["birth_year"] == birth_year(8)

    response = await parent.patch(
        f"/api/children/{child['id']}", json={"birth_year": birth_year(10)}, headers=await csrf_headers(parent)
    )
    assert response.json() == {**response.json(), "name": "An Nhiên", "birth_year": birth_year(10)}


async def test_delete(parent):
    child = (await create_child(parent)).json()
    response = await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))
    assert response.status_code == 204
    assert (await parent.get(f"/api/children/{child['id']}")).status_code == 404
    assert (await parent.get("/api/children")).json() == []


@pytest.mark.parametrize("name", ["", "   ", "x" * 65])
async def test_invalid_name(parent, name):
    response = await create_child(parent, name)
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_name"}


async def test_birth_year_bounds(parent):
    assert (await create_child(parent, "An", 2000)).status_code == 201
    assert (await create_child(parent, "Bình", birth_year(0))).status_code == 201


@pytest.mark.parametrize("year", [1999, "next"])
async def test_invalid_birth_year(parent, year):
    response = await create_child(parent, "An", birth_year(-1) if year == "next" else year)
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_birth_year"}


async def test_update_validates(parent):
    child = (await create_child(parent)).json()
    response = await parent.patch(f"/api/children/{child['id']}", json={"name": " "}, headers=await csrf_headers(parent))
    assert response.json() == {"detail": "invalid_name"}
    assert (await parent.get(f"/api/children/{child['id']}")).json()["name"] == child["name"]


async def test_missing_child_is_404(parent):
    assert (await parent.get("/api/children/9999")).json() == {"detail": "not_found"}


async def test_anonymous_gets_401(client):
    assert (await client.get("/api/children")).status_code == 401
    response = await client.post("/api/children", json={"name": "An", "birth_year": birth_year()}, headers=await csrf_headers(client))
    assert response.status_code == 401


async def test_write_without_csrf_is_rejected(parent):
    response = await parent.post("/api/children", json={"name": "An", "birth_year": birth_year()})
    assert response.status_code == 403
    assert response.json() == {"detail": "csrf_failed"}
