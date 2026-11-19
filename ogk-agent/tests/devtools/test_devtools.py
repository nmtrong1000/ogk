import json
from pathlib import Path

import httpx
import pytest

from service.core import agent as agent_module
from service.core.agent import ModuleContext, dev_routes
from service.core.ipc_server import IPC_FILE, IpcServer
from service.core.policy_store import MODE_DEFAULT
from tests.modules.sync.test_heartbeat import Rig
from tests.policy_vectors import EVENT_VECTORS

pytestmark = pytest.mark.anyio

BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "installer" / "build.ps1"


def context(rig: Rig, data_dir) -> ModuleContext:
    return ModuleContext(
        rig.bus,
        rig.enforcement,
        None,
        data_dir,
        rig.store,
        rig.session,
        event_queue=rig.queue,
        offline=rig.offline,
    )


def test_release_build_excludes_devtools():
    assert "--exclude-module service.devtools" in BUILD_SCRIPT.read_text(encoding="utf-8")


def test_no_routes_without_dev_flag(data_dir, monkeypatch):
    monkeypatch.delenv(agent_module.DEV_ENV, raising=False)
    assert dev_routes(context(Rig(data_dir), data_dir)) == []


def test_no_routes_when_package_missing(data_dir, monkeypatch):
    monkeypatch.setenv(agent_module.DEV_ENV, "1")

    def excluded(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(agent_module.importlib, "import_module", excluded)
    assert dev_routes(context(Rig(data_dir), data_dir)) == []


@pytest.fixture
async def dev_ipc(data_dir, monkeypatch):
    monkeypatch.setenv(agent_module.DEV_ENV, "1")
    rig = Rig(data_dir)
    await rig.session.me()
    server = IpcServer(data_dir, 0, lambda: {}, extra_routes=dev_routes(context(rig, data_dir)))
    await server.start()
    info = json.loads((data_dir / IPC_FILE).read_text(encoding="utf-8"))
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{info['port']}", headers={"Authorization": f"Bearer {info['token']}"}
    ) as client:
        yield rig, client
    await server.stop()


async def test_inject_vector_queues_events_for_this_device(dev_ipc):
    rig, client = dev_ipc
    response = await client.post("/ipc/dev/events", json={"vector": "blocked_domain", "child_id": 7, "count": 3})
    assert response.json() == {"queued": 3, "pending": 3}
    await rig.queue.flush()
    assert [(e["device_id"], e["child_id"], e["subject"]) for e in rig.server.events] == [(1, 7, "youtube.com")] * 3


async def test_inject_rejects_invalid_event(dev_ipc):
    _, client = dev_ipc
    bad = {**EVENT_VECTORS["valid"][0]["event"], "type": "x"}
    response = await client.post("/ipc/dev/events", json={"events": [bad]})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_event", "field": "type"}


async def test_inject_rejects_unknown_vector(dev_ipc):
    _, client = dev_ipc
    assert (await client.post("/ipc/dev/events", json={"vector": "nope"})).status_code == 400


async def test_simulated_offline_days_switch_policy_mode(dev_ipc):
    rig, client = dev_ipc
    response = await client.post("/ipc/dev/offline", json={"days": 7})
    assert response.json()["policy_mode"] == MODE_DEFAULT
    assert rig.store.mode == MODE_DEFAULT
    assert (await client.post("/ipc/dev/offline", json={"days": -1})).status_code == 400
