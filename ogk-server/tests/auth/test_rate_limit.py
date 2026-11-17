import pytest

from app.core.security import RateLimiter
from tests.auth.conftest import login, register

pytestmark = pytest.mark.anyio


async def test_login_rate_limited_per_ip(client):
    for _ in range(10):
        assert (await login(client, "x@example.com")).status_code == 401
    response = await login(client, "x@example.com")
    assert response.status_code == 429
    assert response.json() == {"detail": "rate_limited"}
    assert int(response.headers["retry-after"]) >= 1


async def test_register_rate_limited_per_ip(client):
    for i in range(5):
        client.cookies.delete("ogk_session")
        assert (await register(client, f"r{i}@example.com")).status_code == 201
    response = await register(client, "r5@example.com")
    assert response.status_code == 429


def test_window_slides():
    t = [0.0]
    limiter = RateLimiter(clock=lambda: t[0])
    assert limiter.hit("k", 2, 60) is None
    t[0] = 30
    assert limiter.hit("k", 2, 60) is None
    assert limiter.hit("k", 2, 60) == pytest.approx(30)
    assert limiter.hit("other", 2, 60) is None
    t[0] = 60
    assert limiter.hit("k", 2, 60) is None
