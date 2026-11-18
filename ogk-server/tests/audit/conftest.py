import httpx
import pytest

from tests.conftest import make_client, register


async def audit_page(c: httpx.AsyncClient, page: int = 1, size: int = 20) -> dict:
    response = await c.get("/api/audit", params={"page": page, "size": size})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
async def other_parent(app):
    async with make_client(app) as c:
        assert (await register(c, "other@example.com")).status_code == 201
        yield c
