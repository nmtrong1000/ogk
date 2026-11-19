import httpx
import pytest

from tests.conftest import csrf_headers, make_client, register

DEFAULT_DAY = "0" * 14 + "1" * 28 + "0" * 6
DEFAULT_SCHEDULE = [DEFAULT_DAY] * 7


async def patch_policy(c: httpx.AsyncClient, child_id: int, **body) -> httpx.Response:
    return await c.patch(f"/api/children/{child_id}/policy", json=body, headers=await csrf_headers(c))


async def set_quota(c: httpx.AsyncClient, child_id: int, minutes) -> httpx.Response:
    return await patch_policy(c, child_id, weekday_quota_minutes=minutes)


async def assign(c: httpx.AsyncClient, device_id: int, account_id: int, child_id: int | None) -> httpx.Response:
    return await c.put(
        f"/api/devices/{device_id}/accounts/{account_id}", json={"child_id": child_id}, headers=await csrf_headers(c)
    )


async def device_accounts(c: httpx.AsyncClient, device_id: int) -> list[dict]:
    devices = (await c.get("/api/devices")).json()
    return next(d for d in devices if d["id"] == device_id)["accounts"]


@pytest.fixture
async def agent(app):
    async with make_client(app) as c:
        yield c


@pytest.fixture
async def other_parent(app):
    async with make_client(app) as c:
        assert (await register(c, "other@example.com")).status_code == 201
        yield c
