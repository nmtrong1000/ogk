import asyncio
import json
import threading

import pytest

from service.core.ipc_server import IpcServer
from tray.features.presence.window import describe
from tray.ipc_client import IpcClient, IpcError


@pytest.fixture
def service(tmp_path):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    server = IpcServer(tmp_path, 0, lambda: {"uptime": 2.0, "server_reachable": None})
    asyncio.run_coroutine_threadsafe(server.start(), loop).result(5)
    yield server
    asyncio.run_coroutine_threadsafe(server.stop(), loop).result(5)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(5)
    loop.close()


def test_status_from_service(service, tmp_path):
    status = IpcClient(tmp_path).status()
    assert status == {"status": "ok", "uptime": 2.0, "server_reachable": None}
    assert "Server: chưa kiểm tra" in describe(status)


def test_missing_file_means_service_not_running(tmp_path):
    with pytest.raises(IpcError, match="chưa chạy"):
        IpcClient(tmp_path).status()


def test_wrong_token_rejected(service, tmp_path):
    path = tmp_path / "ipc.json"
    info = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**info, "token": "wrong"}), encoding="utf-8")
    with pytest.raises(IpcError, match="từ chối"):
        IpcClient(tmp_path).status()


def test_service_gone_is_reported(tmp_path):
    (tmp_path / "ipc.json").write_text(json.dumps({"port": 1, "token": "t"}), encoding="utf-8")
    with pytest.raises(IpcError, match="Không kết nối"):
        IpcClient(tmp_path, timeout=1).status()


def test_corrupt_file_is_reported(tmp_path):
    (tmp_path / "ipc.json").write_text("{", encoding="utf-8")
    with pytest.raises(IpcError, match="không hợp lệ"):
        IpcClient(tmp_path).status()
