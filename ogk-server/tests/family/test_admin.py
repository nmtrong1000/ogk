import pytest

from tests.conftest import csrf_headers
from tests.family.conftest import birth_year, create_child

pytestmark = pytest.mark.anyio


async def test_admin_cannot_read_children(parent, admin):
    child = (await create_child(parent)).json()

    for response in [await admin.get("/api/children"), await admin.get(f"/api/children/{child['id']}")]:
        assert response.status_code == 403
        assert response.json() == {"detail": "forbidden"}


async def test_admin_cannot_write_children(parent, admin):
    child = (await create_child(parent)).json()
    headers = await csrf_headers(admin)
    url = f"/api/children/{child['id']}"
    assert (
        await admin.post("/api/children", json={"name": "X", "birth_year": birth_year()}, headers=headers)
    ).status_code == 403
    assert (await admin.patch(url, json={"name": "X"}, headers=headers)).status_code == 403
    assert (await admin.delete(url, headers=headers)).status_code == 403
    assert (await parent.get(url)).json() == child


async def test_admin_api_does_not_expose_children(parent, admin):
    await create_child(parent, "Bé An")
    body = (await admin.get("/api/admin/accounts")).text
    assert "Bé An" not in body
