import asyncio
import logging

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from service.core.bus import POLICY, Bus
from service.core.device_session import DeviceSession
from service.core.local_db import LocalDb
from service.core.policy_store import PolicyStore
from service.modules.policy import PolicyLoader
from tests.core.test_device_session import CONFIG, enrolled
from tests.fake_server import FakeServer
from tests.policy_vectors import body, document, envelope, write_public_key

pytestmark = pytest.mark.anyio


@pytest.fixture
def server():
    return FakeServer()


def make_loader(server: FakeServer, data_dir, bus: Bus | None = None) -> PolicyLoader:
    db = LocalDb(data_dir)
    session = DeviceSession(CONFIG, db, client_factory=server.client, clock=lambda: server.now)
    return PolicyLoader(PolicyStore(db, write_public_key(data_dir)), session, bus or Bus())


async def test_startup_downloads_and_logs_version(server, data_dir, caplog):
    enrolled(server, LocalDb(data_dir))
    server.policy_body = body(document(7, 1))
    bus = Bus()
    published = []
    bus.subscribe(POLICY, published.append)
    with caplog.at_level(logging.INFO, logger="ogk.policy"):
        assert await make_loader(server, data_dir, bus).tick()
    assert "policy loaded from server: child=7 version=1" in caplog.text
    assert [p.keys() for p in published] == [{7}]


async def test_restart_loads_newest_policy(server, data_dir, caplog):
    enrolled(server, LocalDb(data_dir))
    server.policy_body = body(document(7, 1))
    await make_loader(server, data_dir).tick()
    server.policy_body = body(document(7, 2, quota=45))
    restarted = make_loader(server, data_dir)
    with caplog.at_level(logging.INFO, logger="ogk.policy"):
        await restarted.load_cached()
        await restarted.tick()
    assert "policy loaded from cache: child=7 version=1" in caplog.text
    assert "policy loaded from server: child=7 version=2" in caplog.text
    assert restarted._store.current()[7].document["rules"]["weekday_quota_minutes"] == 45


async def test_bad_signature_from_server_keeps_cache(server, data_dir, caplog):
    enrolled(server, LocalDb(data_dir))
    server.policy_body = body(document(7, 1))
    loader = make_loader(server, data_dir)
    await loader.tick()
    server.policy_body = {"policies": [envelope(document(7, 2), key=Ed25519PrivateKey.generate())]}
    with caplog.at_level(logging.ERROR, logger="ogk.policy"):
        assert not await loader.tick()
    assert "rejected" in caplog.text
    assert loader._store.versions() == {7: 1}


async def test_server_unreachable_uses_cache(server, data_dir, caplog):
    enrolled(server, LocalDb(data_dir))
    server.policy_body = body(document(7, 1))
    await make_loader(server, data_dir).tick()

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    server.handle = unreachable
    loader = make_loader(server, data_dir)
    with caplog.at_level(logging.INFO, logger="ogk.policy"):
        await loader.load_cached()
        assert not await loader.tick()
    assert "keeping cached policies" in caplog.text
    assert loader._store.versions() == {7: 1}


async def test_not_enrolled_skips_download(server, data_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="ogk.policy"):
        assert not await make_loader(server, data_dir).tick()
    assert "not enrolled" in caplog.text
    assert ("GET", "/api/device/policy") not in server.requests


async def test_run_keeps_running_after_download(server, data_dir):
    enrolled(server, LocalDb(data_dir))
    task = asyncio.create_task(make_loader(server, data_dir).run())
    await asyncio.sleep(0.05)
    assert not task.done()
    task.cancel()
