"""The agent client is a separate httpx client with no cookies, like the real agent, so CSRF never applies."""

from datetime import datetime, timedelta

import httpx
import pytest

from app.modules.enrollment import service as enrollment_service
from tests.conftest import csrf_headers, make_client, register

SECRET = "s" * 43
ACCOUNTS = [
    {"sid": "S-1-5-21-1-1001", "username": "an"},
    {"sid": "S-1-5-21-1-1002", "username": "binh"},
]


async def create_code(c: httpx.AsyncClient, consent: bool = True) -> httpx.Response:
    return await c.post("/api/pairing-codes", json={"consent": consent}, headers=await csrf_headers(c))


def enroll_body(code: str, **overrides) -> dict:
    body = {
        "code": code,
        "fingerprint": "f" * 64,
        "device_secret": SECRET,
        "name": "PC phòng khách",
        "accounts": ACCOUNTS,
    }
    body.update(overrides)
    return body


async def enroll(agent: httpx.AsyncClient, code: str, **overrides) -> httpx.Response:
    return await agent.post("/api/enroll", json=enroll_body(code, **overrides))


async def enroll_device(parent: httpx.AsyncClient, agent: httpx.AsyncClient, **overrides) -> dict:
    code = (await create_code(parent)).json()["code"]
    response = await enroll(agent, code, **overrides)
    assert response.status_code == 201, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def agent(app):
    async with make_client(app) as c:
        yield c


class Clock:
    def __init__(self, monkeypatch) -> None:
        self.at = enrollment_service.now()
        monkeypatch.setattr(enrollment_service, "now", lambda: self.at)

    def advance(self, **kwargs) -> datetime:
        self.at += timedelta(**kwargs)
        return self.at


@pytest.fixture
def clock(monkeypatch) -> Clock:
    return Clock(monkeypatch)


@pytest.fixture
async def other_parent(app):
    async with make_client(app) as c:
        assert (await register(c, "other@example.com")).status_code == 201
        yield c
