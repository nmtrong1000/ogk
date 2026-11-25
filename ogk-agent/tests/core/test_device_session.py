import asyncio
import logging
from datetime import timedelta

import pytest

from service.core.config import Config
from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.local_db import Credentials, LocalDb
from service.core.server_client import ApiError
from tests.fake_server import PIN, FakeServer

pytestmark = pytest.mark.anyio

CONFIG = Config(server_url="https://server", ca_cert=None)


def enrolled(server: FakeServer, db: LocalDb) -> None:
    server.secret = "secret"
    tokens = server._tokens()
    db.save(
        Credentials(
            device_id=1,
            server_url="https://server",
            cert_sha256=PIN,
            device_secret="secret",
            access_token=tokens["access_token"],
            access_expires_at=server.now + timedelta(minutes=15),
            refresh_token=tokens["refresh_token"],
            enrolled_at=server.now,
        )
    )


@pytest.fixture
def server():
    return FakeServer()


@pytest.fixture
def db(data_dir):
    return LocalDb(data_dir)


@pytest.fixture
def session(server, db):
    return DeviceSession(CONFIG, db, client_factory=server.client, clock=lambda: server.now)


async def test_not_enrolled(session, server):
    with pytest.raises(NotEnrolled):
        await session.me()
    assert session.state == "not_enrolled"
    assert server.requests == []


async def test_uses_access_token(session, server, db):
    enrolled(server, db)
    assert await session.me() == {"id": 1, "name": "PC"}
    assert server.requests == [("GET", "/api/device/me")]
    assert session.state == "active"


async def test_child_view_retry_can_use_fresh_client(session, server, db):
    enrolled(server, db)
    result = await session.create_child_view_code_fresh(9, "c" * 43)
    assert result == {"expires_at": "2026-11-19T08:01:00Z"}
    assert server.requests == [("POST", "/api/device/child-view-codes")]


async def test_refreshes_before_expiry(session, server, db, caplog):
    caplog.set_level(logging.INFO)
    enrolled(server, db)
    server.now += timedelta(minutes=14, seconds=30)
    await session.me()
    assert server.requests == [("POST", "/api/device/token/refresh"), ("GET", "/api/device/me")]
    stored = db.load()
    assert stored.access_token == "access-2"
    assert stored.refresh_token == "refresh-2"
    assert "access token refreshed" in caplog.text


async def test_refreshes_after_15_minutes(session, server, db):
    enrolled(server, db)
    server.now += timedelta(minutes=20)
    assert await session.me() == {"id": 1, "name": "PC"}
    assert db.load().access_token == "access-2"


async def test_retries_once_on_token_expired(session, server, db):
    enrolled(server, db)
    server.access = {k: server.now for k in server.access}
    await session.me()
    assert server.requests == [
        ("GET", "/api/device/me"),
        ("POST", "/api/device/token/refresh"),
        ("GET", "/api/device/me"),
    ]


async def test_revoked_stops_api_calls(session, server, db, caplog):
    enrolled(server, db)
    server.revoked = True
    with pytest.raises(DeviceRevoked):
        await session.me()
    assert "device 1 revoked by server (device_revoked); API calls stopped" in caplog.text
    assert session.state == "revoked"
    assert db.load().revoked_at is not None
    calls = len(server.requests)
    with pytest.raises(DeviceRevoked):
        await session.me()
    assert len(server.requests) == calls


async def test_revoked_found_during_refresh(session, server, db, caplog):
    enrolled(server, db)
    server.revoked = True
    server.now += timedelta(minutes=20)
    with pytest.raises(DeviceRevoked):
        await session.me()
    assert server.requests == [("POST", "/api/device/token/refresh")]
    assert "revoked by server (device_revoked)" in caplog.text


async def test_invalid_refresh_is_final(session, server, db, caplog):
    enrolled(server, db)
    server.refresh_token = "rotated-elsewhere"
    server.now += timedelta(minutes=20)
    with pytest.raises(DeviceRevoked):
        await session.me()
    assert "invalid_refresh" in caplog.text
    assert session.state == "revoked"


async def test_revoked_state_survives_restart(server, db):
    enrolled(server, db)
    db.mark_revoked(db.load(), server.now)
    session = DeviceSession(CONFIG, db, client_factory=server.client, clock=lambda: server.now)
    with pytest.raises(DeviceRevoked):
        await session.me()
    assert server.requests == []


async def test_picks_up_new_enrollment_without_restart(session, server, db):
    with pytest.raises(NotEnrolled):
        await session.me()
    enrolled(server, db)
    assert await session.me() == {"id": 1, "name": "PC"}


async def test_other_errors_propagate(session, server, db):
    enrolled(server, db)
    with pytest.raises(ApiError) as info:
        await session.call(lambda client, token: client._json("GET", "/api/nope"))
    assert info.value.code == "not_found"


async def test_enrollment_for_other_server_is_ignored(server, db):
    enrolled(server, db)
    session = DeviceSession(Config(server_url="https://elsewhere", ca_cert=None), db, client_factory=server.client)
    with pytest.raises(NotEnrolled):
        await session.me()


async def test_client_is_built_with_stored_pin(server, db):
    enrolled(server, db)
    pins = []

    def factory(config, pin):
        pins.append(pin)
        return server.client()

    session = DeviceSession(CONFIG, db, client_factory=factory, clock=lambda: server.now)
    await session.me()
    await session.me()
    assert pins == [PIN]
    await session.aclose()


async def test_concurrent_calls_share_one_refresh(session, server, db):
    enrolled(server, db)
    await session.me()
    server.requests.clear()
    server.now += timedelta(minutes=20)
    results = await asyncio.gather(session.me(), session.me(), session.me())
    assert results == [{"id": 1, "name": "PC"}] * 3
    assert server.requests.count(("POST", "/api/device/token/refresh")) == 1
    assert session.state == "active"
    assert db.load().revoked_at is None


async def test_concurrent_retries_share_one_refresh(session, server, db):
    enrolled(server, db)
    await session.me()
    server.requests.clear()
    server.access = {k: server.now for k in server.access}
    results = await asyncio.gather(session.me(), session.me(), session.me())
    assert results == [{"id": 1, "name": "PC"}] * 3
    assert server.requests.count(("POST", "/api/device/token/refresh")) == 1
    assert session.state == "active"
