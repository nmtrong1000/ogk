import asyncio
import json
import os
import threading

import pytest

from service.core.bus import TrayPing
from service.core.ipc_server import IpcServer
from tray.features.presence.window import describe, describe_error
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
    with pytest.raises(IpcError, match="not running") as info:
        IpcClient(tmp_path).status()
    assert info.value.code == "not_running"
    assert describe_error(info.value) == "Service chưa chạy"


def test_wrong_token_rejected(service, tmp_path):
    path = tmp_path / "ipc.json"
    info = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**info, "token": "wrong"}), encoding="utf-8")
    with pytest.raises(IpcError, match="rejected") as info:
        IpcClient(tmp_path).status()
    assert info.value.code == "unauthorized"


def test_service_gone_is_reported(tmp_path):
    (tmp_path / "ipc.json").write_text(json.dumps({"port": 1, "token": "t"}), encoding="utf-8")
    with pytest.raises(IpcError, match="Cannot connect") as info:
        IpcClient(tmp_path, timeout=1).status()
    assert info.value.code == "unreachable"
    assert describe_error(info.value) == "Không kết nối được service"


def test_corrupt_file_is_reported(tmp_path):
    (tmp_path / "ipc.json").write_text("{", encoding="utf-8")
    with pytest.raises(IpcError, match="Invalid IPC file") as info:
        IpcClient(tmp_path).status()
    assert info.value.code == "bad_ipc_file"


def test_heartbeat_reaches_service(tmp_path):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    pids = []
    server = IpcServer(tmp_path, 0, dict, pids.append)
    asyncio.run_coroutine_threadsafe(server.start(), loop).result(5)
    try:
        IpcClient(tmp_path).heartbeat()
        IpcClient(tmp_path).heartbeat(312.04)
        IpcClient(tmp_path).heartbeat(None, "game.exe")
    finally:
        asyncio.run_coroutine_threadsafe(server.stop(), loop).result(5)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)
        loop.close()
    assert pids == [
        TrayPing(os.getpid(), None),
        TrayPing(os.getpid(), 312.0),
        TrayPing(os.getpid(), None, "game.exe"),
    ]


def test_heartbeat_without_service_raises(tmp_path):
    with pytest.raises(IpcError) as info:
        IpcClient(tmp_path).heartbeat()
    assert info.value.code == "not_running"


def test_screentime_reaches_service(tmp_path):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    server = IpcServer(tmp_path, 0, dict, screen_provider=lambda: {"state": "ok", "remaining_seconds": 60})
    asyncio.run_coroutine_threadsafe(server.start(), loop).result(5)
    try:
        snapshot = IpcClient(tmp_path).screentime()
    finally:
        asyncio.run_coroutine_threadsafe(server.stop(), loop).result(5)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)
        loop.close()
    assert snapshot == {"status": "ok", "state": "ok", "remaining_seconds": 60}
