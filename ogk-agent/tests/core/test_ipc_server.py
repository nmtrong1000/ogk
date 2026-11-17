import json
import os
import stat

import httpx
import pytest

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
