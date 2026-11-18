from datetime import timedelta

import pytest

from app.core.db import utcnow
from app.modules.auth import service
from tests.conftest import login, make_client, register

pytestmark = pytest.mark.anyio

EMAIL = "p@example.com"


@pytest.fixture
async def account(app, client):
    async with make_client(app) as other:
        assert (await register(other, EMAIL)).status_code == 201


async def test_login_ok(client, account):
    response = await login(client, EMAIL)
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


async def test_unknown_email_same_error_as_wrong_password(client, account):
    unknown = await login(client, "nobody@example.com")
    wrong = await login(client, EMAIL, "sai-mat-khau-0")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "invalid_credentials"}


async def test_fifth_failure_locks_for_15_minutes(client, account, monkeypatch):
    start = utcnow()
    monkeypatch.setattr(service, "now", lambda: start)

    for _ in range(4):
        assert (await login(client, EMAIL, "sai-mat-khau-0")).status_code == 401

    fifth = await login(client, EMAIL, "sai-mat-khau-0")
    assert fifth.status_code == 423
    assert fifth.json()["detail"] == "account_locked"
    assert fifth.json()["locked_until"].endswith("Z")

    # Đang khóa thì đúng mật khẩu vẫn bị từ chối.
    assert (await login(client, EMAIL)).status_code == 423

    monkeypatch.setattr(service, "now", lambda: start + timedelta(minutes=14, seconds=59))
    assert (await login(client, EMAIL)).status_code == 423

    monkeypatch.setattr(service, "now", lambda: start + timedelta(minutes=15, seconds=1))
    assert (await login(client, EMAIL)).status_code == 200


async def test_success_resets_failure_counter(client, account):
    for _ in range(4):
        await login(client, EMAIL, "sai-mat-khau-0")
    assert (await login(client, EMAIL)).status_code == 200
    for _ in range(4):
        assert (await login(client, EMAIL, "sai-mat-khau-0")).status_code == 401
