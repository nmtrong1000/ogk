import asyncio
import json
import logging

import httpx
import pytest

from service.core.agent import Agent
from service.core.bus import TRAY_HEARTBEAT, Bus
from service.core.config import Config
from service.core.enforcement import Enforcement
from service.core.local_db import LocalDb
from service.core.policy_store import PolicyStore
from tests.policy_vectors import body, document, write_public_key


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.closed = False
        self.called = asyncio.Event()

    async def health(self):
        self.calls += 1
        self.called.set()
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def aclose(self):
        self.closed = True


def _config():
    return Config(server_url="https://server", ca_cert=None, health_interval=0.01, ipc_port=0)


@pytest.mark.anyio
async def test_agent_logs_health_and_stops(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    client = FakeClient({"status": "ok"})
    stop_event = asyncio.Event()
    run = asyncio.create_task(Agent(_config(), client, tmp_path).run(stop_event))
    await asyncio.wait_for(client.called.wait(), 1)
    assert (tmp_path / "ipc.json").exists()
    stop_event.set()
    await asyncio.wait_for(run, 1)
    assert client.closed
    assert not (tmp_path / "ipc.json").exists()
    assert "server ok" in caplog.text
    assert "agent stopped" in caplog.text


@pytest.mark.anyio
async def test_unreachable_server_is_logged_not_raised(caplog, tmp_path):
    client = FakeClient(httpx.ConnectError("refused"))
    agent = Agent(_config(), client, tmp_path)
    assert await agent.check_health() is False
    assert agent.status()["server_reachable"] is False
    assert "server unreachable: refused" in caplog.text


@pytest.mark.anyio
async def test_unexpected_error_stops_agent(tmp_path):
    client = FakeClient(RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await asyncio.wait_for(Agent(_config(), client, tmp_path).run(asyncio.Event()), 1)
    assert client.closed
    assert not (tmp_path / "ipc.json").exists()


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.state = "active"
        self.closed = False

    async def me(self):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def aclose(self):
        self.closed = True


@pytest.mark.anyio
async def test_device_check_logs_changes_once(caplog, tmp_path):
    from service.core.device_session import DeviceRevoked, NotEnrolled
    from service.core.server_client import CertificatePinError

    caplog.set_level(logging.INFO)
    session = FakeSession(
        [
            NotEnrolled(),
            NotEnrolled(),
            {"id": 1, "name": "PC"},
            CertificatePinError("server certificate x does not match pinned y"),
            DeviceRevoked(),
            DeviceRevoked(),
        ]
    )
    agent = Agent(_config(), FakeClient({"status": "ok"}), tmp_path, session)
    results = [await agent.check_device() for _ in range(6)]
    assert results == [False, False, True, False, False, False]
    assert caplog.text.count("device not enrolled") == 1
    assert "device 1 authenticated as PC" in caplog.text
    assert "refusing to connect: server certificate x does not match pinned y" in caplog.text
    assert caplog.text.count("device is revoked; API calls stopped") == 1
    assert agent.status()["enrollment"] == "active"


@pytest.mark.anyio
async def test_status_includes_enforcement(tmp_path):
    enforcement = Enforcement()
    agent = Agent(_config(), FakeClient({"status": "ok"}), tmp_path, enforcement=enforcement)
    assert agent.status()["enforcement"]["enabled"] is True
    enforcement.disable("tray_unavailable")
    assert agent.status()["enforcement"] == enforcement.snapshot()


class FakeModule:
    def __init__(self):
        self.started = asyncio.Event()
        self.cancelled = False

    async def run(self):
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


@pytest.mark.anyio
async def test_modules_run_and_stop_with_agent(tmp_path):
    module = FakeModule()
    stop_event = asyncio.Event()
    agent = Agent(_config(), FakeClient({"status": "ok"}), tmp_path, modules=[module])
    run = asyncio.create_task(agent.run(stop_event))
    await asyncio.wait_for(module.started.wait(), 1)
    stop_event.set()
    await asyncio.wait_for(run, 1)
    assert module.cancelled


@pytest.mark.anyio
async def test_ipc_heartbeat_is_published_on_bus(tmp_path):
    bus = Bus()
    pids = []
    bus.subscribe(TRAY_HEARTBEAT, pids.append)
    client = FakeClient({"status": "ok"})
    stop_event = asyncio.Event()
    run = asyncio.create_task(Agent(_config(), client, tmp_path, bus=bus).run(stop_event))
    await asyncio.wait_for(client.called.wait(), 1)
    info = json.loads((tmp_path / "ipc.json").read_text(encoding="utf-8"))
    async with httpx.AsyncClient() as http:
        response = await http.post(
            f"http://127.0.0.1:{info['port']}/ipc/heartbeat",
            json={"pid": 7},
            headers={"Authorization": f"Bearer {info['token']}"},
        )
    stop_event.set()
    await asyncio.wait_for(run, 1)
    assert response.status_code == 200
    assert pids == [7]


@pytest.mark.anyio
async def test_status_includes_policy_versions(data_dir):
    store = PolicyStore(LocalDb(data_dir), write_public_key(data_dir))
    agent = Agent(_config(), FakeClient({"status": "ok"}), data_dir, policy_store=store)
    assert agent.status()["policies"] == {}
    store.save(body(document(7, 2)))
    assert agent.status()["policies"] == {7: 2}
