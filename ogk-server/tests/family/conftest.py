import httpx
import pytest

from tests.conftest import csrf_headers, make_client, register



def birth_year(age: int = 8) -> int:
    from app.modules.family.service import now

    return now().year - age


async def create_child(c: httpx.AsyncClient, name: str = "Bé An", year: int | None = None) -> httpx.Response:
    return await c.post(
        "/api/children", json={"name": name, "birth_year": year or birth_year()}, headers=await csrf_headers(c)
    )


@pytest.fixture
async def other_parent(app):
    """Client của phụ huynh thứ hai (B)."""
    async with make_client(app) as c:
        assert (await register(c, "other@example.com")).status_code == 201
        yield c
