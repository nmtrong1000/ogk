import pytest

from app.cli import main as cli_main
from app.core.db import get_sessionmaker
from app.modules.auth import service
from tests.auth.conftest import PASSWORD, login, register
from tests.conftest import csrf_headers, make_client

pytestmark = pytest.mark.anyio

EMAIL = "p@example.com"


async def _lock_parent(app) -> int:
    async with make_client(app) as c:
        account_id = (await register(c, EMAIL)).json()["id"]
        for _ in range(5):
            await login(c, EMAIL, "sai-mat-khau-0")
        assert (await login(c, EMAIL)).status_code == 423
    return account_id


async def test_admin_unlocks_parent(app, admin):
    account_id = await _lock_parent(app)

    locked = await admin.get("/api/admin/accounts", params={"locked": "true"})
    assert [a["id"] for a in locked.json()] == [account_id]
    assert locked.json()[0]["locked_until"].endswith("Z")

    response = await admin.post(f"/api/admin/accounts/{account_id}/unlock", headers=await csrf_headers(admin))
    assert response.status_code == 200
    assert response.json() == {"id": account_id, "email": EMAIL, "failed_attempts": 0, "locked_until": None}
    assert (await admin.get("/api/admin/accounts", params={"locked": "true"})).json() == []

    async with make_client(app) as c:
        assert (await login(c, EMAIL)).status_code == 200


async def test_parent_cannot_unlock(app, parent):
    account_id = await _lock_parent(app)
    response = await parent.post(f"/api/admin/accounts/{account_id}/unlock", headers=await csrf_headers(parent))
    assert response.status_code == 403


async def test_unlock_unknown_or_admin_account_is_404(admin):
    headers = await csrf_headers(admin)
    assert (await admin.post("/api/admin/accounts/999/unlock", headers=headers)).status_code == 404
    me = (await admin.get("/api/auth/me")).json()
    assert (await admin.post(f"/api/admin/accounts/{me['id']}/unlock", headers=headers)).status_code == 404


async def test_admin_list_excludes_admins(admin, app):
    async with make_client(app) as c:
        await register(c, EMAIL)
    emails = [a["email"] for a in (await admin.get("/api/admin/accounts")).json()]
    assert emails == [EMAIL]


async def test_cli_create_admin(app, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": PASSWORD)
    # asyncio.run trong CLI cần chạy ở thread khác event loop của test.
    from starlette.concurrency import run_in_threadpool

    assert await run_in_threadpool(cli_main, ["create-admin", "Boss@OGK.local"]) == 0
    assert "boss@ogk.local" in capsys.readouterr().out
    async with get_sessionmaker()() as db:
        account = await service.get_by_email(db, "boss@ogk.local")
    assert account.role == "admin"


async def test_cli_rejects_short_password(app, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": "ngan")
    from starlette.concurrency import run_in_threadpool

    assert await run_in_threadpool(cli_main, ["create-admin", "boss@ogk.local"]) == 1
    assert "ít nhất 10" in capsys.readouterr().err
