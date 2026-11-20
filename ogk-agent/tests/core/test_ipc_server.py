import json
import os
import stat

import httpx
import pytest

from service.core.bus import TrayPing
from service.core.ipc_server import IPC_FILE, IpcServer


@pytest.fixture
async def ipc(tmp_path):
    server = IpcServer(tmp_path, 0, lambda: {"uptime": 1.0, "server_reachable": True})
    await server.start()
    yield server
    await server.stop()


def _read(tmp_path):
    return json.loads((tmp_path / IPC_FILE).read_text(encoding="utf-8"))


async def _get(port, headers=None):
    async with httpx.AsyncClient() as client:
        return await client.get(f"http://127.0.0.1:{port}/ipc/status", headers=headers)


@pytest.mark.anyio
async def test_status_with_token(ipc, tmp_path):
    info = _read(tmp_path)
    assert info["port"] == ipc.port != 0
    response = await _get(ipc.port, {"Authorization": f"Bearer {info['token']}"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "uptime": 1.0, "server_reachable": True}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Bearer wrong"}, {"Authorization": "Bearer"}],
)
async def test_request_without_valid_token_rejected(ipc, headers):
    response = await _get(ipc.port, headers)
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


@pytest.mark.anyio
async def test_token_wrong_scheme_rejected(ipc, tmp_path):
    token = _read(tmp_path)["token"]
    response = await _get(ipc.port, {"Authorization": f"Basic {token}"})
    assert response.status_code == 401


@pytest.mark.anyio
@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
async def test_token_file_read_only_for_users(ipc, tmp_path):
    mode = stat.S_IMODE((tmp_path / IPC_FILE).stat().st_mode)
    assert mode == 0o644


@pytest.mark.anyio
async def test_new_token_each_start_and_file_removed_on_stop(tmp_path):
    tokens = []
    for _ in range(2):
        server = IpcServer(tmp_path, 0, dict)
        await server.start()
        tokens.append(_read(tmp_path)["token"])
        await server.stop()
        assert not (tmp_path / IPC_FILE).exists()
    assert tokens[0] != tokens[1]
    assert len(tokens[0]) >= 40


@pytest.fixture
async def ipc_with_heartbeat(tmp_path):
    pids = []
    server = IpcServer(tmp_path, 0, dict, pids.append)
    await server.start()
    yield server, pids
    await server.stop()


async def _post(port, body, headers):
    async with httpx.AsyncClient() as client:
        return await client.post(f"http://127.0.0.1:{port}/ipc/heartbeat", json=body, headers=headers)


@pytest.mark.anyio
async def test_heartbeat_with_token_reaches_handler(ipc_with_heartbeat, tmp_path):
    server, pids = ipc_with_heartbeat
    token = _read(tmp_path)["token"]
    response = await _post(server.port, {"pid": 4242}, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert pids == [TrayPing(4242, None)]


@pytest.mark.anyio
async def test_heartbeat_carries_idle_seconds(ipc_with_heartbeat, tmp_path):
    server, pids = ipc_with_heartbeat
    token = _read(tmp_path)["token"]
    response = await _post(server.port, {"pid": 4242, "idle_seconds": 301}, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert pids == [TrayPing(4242, 301.0)]


@pytest.mark.anyio
async def test_heartbeat_without_token_rejected(ipc_with_heartbeat):
    server, pids = ipc_with_heartbeat
    response = await _post(server.port, {"pid": 4242}, None)
    assert response.status_code == 401
    assert pids == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {},
        {"pid": "1"},
        {"pid": True},
        {"pid": 0},
        {"pid": 1, "idle_seconds": -1},
        {"pid": 1, "idle_seconds": "5"},
        {"pid": 1, "idle_seconds": True},
        {"pid": 1, "foreground": ""},
        {"pid": 1, "foreground": 5},
        {"pid": 1, "foreground": "C:\\Games\\game.exe"},
        {"pid": 1, "foreground": "a/b.exe"},
        {"pid": 1, "foreground": "x" * 256},
    ],
)
async def test_heartbeat_bad_body_rejected(ipc_with_heartbeat, tmp_path, body):
    server, pids = ipc_with_heartbeat
    token = _read(tmp_path)["token"]
    response = await _post(server.port, body, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert response.json() == {"error": "bad_request"}
    assert pids == []


@pytest.mark.anyio
async def test_screentime_route_returns_snapshot(tmp_path):
    server = IpcServer(tmp_path, 0, dict, screen_provider=lambda: {"state": "locked", "lock_seq": 2})
    await server.start()
    token = _read(tmp_path)["token"]
    try:
        async with httpx.AsyncClient() as client:
            url = f"http://127.0.0.1:{server.port}/ipc/screentime"
            ok = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            denied = await client.get(url)
    finally:
        await server.stop()
    assert ok.json() == {"status": "ok", "state": "locked", "lock_seq": 2}
    assert denied.status_code == 401


@pytest.mark.anyio
async def test_heartbeat_carries_lowercase_foreground(ipc_with_heartbeat, tmp_path):
    server, pids = ipc_with_heartbeat
    token = _read(tmp_path)["token"]
    body = {"pid": 4242, "idle_seconds": 1, "foreground": "Chrome.EXE"}
    response = await _post(server.port, body, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert pids == [TrayPing(4242, 1.0, "chrome.exe")]


@pytest.mark.anyio
async def test_appcontrol_route_returns_snapshot(tmp_path):
    server = IpcServer(tmp_path, 0, dict, app_provider=lambda: {"block_seq": 1, "app": "game.exe"})
    await server.start()
    token = _read(tmp_path)["token"]
    try:
        async with httpx.AsyncClient() as client:
            url = f"http://127.0.0.1:{server.port}/ipc/appcontrol"
            ok = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            denied = await client.get(url)
    finally:
        await server.stop()
    assert ok.json() == {"status": "ok", "block_seq": 1, "app": "game.exe"}
    assert denied.status_code == 401
