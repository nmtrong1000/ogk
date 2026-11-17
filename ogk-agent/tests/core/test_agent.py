import asyncio
import logging

import httpx
import pytest

from service.core.agent import Agent
from service.core.config import Config


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
