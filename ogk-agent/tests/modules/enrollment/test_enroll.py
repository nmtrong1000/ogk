import pytest

from service.core.local_db import LocalDb
from service.main import main
from service.modules.enrollment.command import enroll
from tests.fake_server import PIN, VALID_CODE, FakeServer

pytestmark = pytest.mark.anyio


@pytest.fixture
def setup(data_dir, write_config):
    write_config({"server_url": "https://server", "ca_cert": "ca.crt"})
    return data_dir


async def run(data_dir, server: FakeServer, code: str = VALID_CODE, **kwargs):
    lines: list[str] = []
    result = await enroll(data_dir, code, client_factory=server.client, out=lines.append, **kwargs)
    return result, "\n".join(lines)


async def test_enroll_saves_credentials(setup):
    server = FakeServer()
    result, output = await run(setup, server)
    assert result == 0
    assert "Enrolled as device 1 with 2 Windows account(s)" in output
    creds = LocalDb(setup).load()
    assert creds.device_id == 1
    assert creds.cert_sha256 == PIN
    assert creds.access_token == "access-1"
    assert creds.refresh_token == "refresh-1"
    assert creds.device_secret == server.secret
    assert creds.server_url == "https://server"


async def test_enroll_sends_fingerprint_and_accounts(setup, monkeypatch):
    monkeypatch.setenv("OGK_FAKE_ACCOUNTS", "an:S-1-5-21-9-1001,binh:S-1-5-21-9-1002,chi:S-1-5-21-9-1003")
    server = FakeServer()
    await run(setup, server)
    body = server.enroll_bodies[0]
    assert len(body["fingerprint"]) == 64
    assert len(body["device_secret"]) >= 32
    assert body["name"]
    assert body["accounts"] == [
        {"username": "an", "sid": "S-1-5-21-9-1001"},
        {"username": "binh", "sid": "S-1-5-21-9-1002"},
        {"username": "chi", "sid": "S-1-5-21-9-1003"},
    ]


async def test_needs_admin(setup, monkeypatch):
    monkeypatch.setenv("OGK_FAKE_ADMIN", "0")
    server = FakeServer()
    result, output = await run(setup, server)
    assert result == 1
    assert "Administrator" in output
    assert server.requests == []


async def test_invalid_code(setup):
    result, output = await run(setup, FakeServer(), code="WRONG")
    assert result == 1
    assert "invalid, expired or already used" in output
    assert LocalDb(setup).load() is None


async def test_already_enrolled_needs_force(setup):
    assert (await run(setup, FakeServer()))[0] == 0
    server = FakeServer()
    result, output = await run(setup, server)
    assert result == 1
    assert "--force" in output
    assert server.requests == []
    assert (await run(setup, server, force=True))[0] == 0


async def test_revoked_device_can_enroll_again(setup):
    await run(setup, FakeServer())
    db = LocalDb(setup)
    db.mark_revoked(db.load(), db.load().enrolled_at)
    result, _ = await run(setup, FakeServer())
    assert result == 0
    assert db.load().revoked_at is None


async def test_missing_config(data_dir):
    result, output = await run(data_dir, FakeServer())
    assert result == 1
    assert "Config file not found" in output


def test_main_routes_enroll_without_code(setup, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit) as info:
        main(["ogk_service.py", "enroll"])
    assert info.value.code == 2
