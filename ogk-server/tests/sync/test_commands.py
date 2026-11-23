import asyncio
import json

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.db import get_engine, get_sessionmaker
from app.modules.audit.service import Actor
from app.modules.sync import commands
from tests.conftest import csrf_headers
from tests.sync.conftest import heartbeat_body, mapped_device, send_heartbeat

pytestmark = pytest.mark.anyio


async def test_parent_command_is_audited_listed_and_redelivered_until_ack(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    path = f"/api/devices/{tokens['device_id']}/children/{child['id']}/commands"
    response = await parent.post(path, json={"type": "add_time"}, headers=await csrf_headers(parent))
    assert response.status_code == 201
    command = response.json()
    assert command["minutes"] == 15
    assert command["status"] == "pending"

    first = await send_heartbeat(agent, tokens["access_token"], heartbeat_body())
    second = await send_heartbeat(agent, tokens["access_token"], heartbeat_body())
    assert first.json()["commands"] == second.json()["commands"] == [command]

    ack = await agent.post(
        f"/api/device/commands/{command['id']}/ack",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert ack.json() == {"acknowledged": True}
    assert (await send_heartbeat(agent, tokens["access_token"], heartbeat_body())).json()["commands"] == []
    listed = await parent.get(path)
    assert listed.json()[0]["status"] == "acknowledged"


async def test_parent_cannot_command_unassigned_child(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    path = f"/api/devices/{tokens['device_id']}/children/{child['id']}/commands"
    response = await parent.post(path, json={"type": "lock"}, headers=await csrf_headers(parent))
    assert response.status_code == 201
    wrong = await parent.post(
        f"/api/devices/{tokens['device_id']}/children/{child['id'] + 100}/commands",
        json={"type": "unlock"},
        headers=await csrf_headers(parent),
    )
    assert wrong.status_code == 404


async def test_rejects_invalid_command(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    response = await parent.post(
        f"/api/devices/{tokens['device_id']}/children/{child['id']}/commands",
        json={"type": "erase"},
        headers=await csrf_headers(parent),
    )
    assert response.status_code == 422


async def test_websocket_closes_for_invalid_device_token(app):
    await get_engine().dispose()
    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDisconnect) as error,
        client.websocket_connect("/api/device/ws", headers={"Authorization": "Bearer invalid-token"}),
    ):
        pass
    assert error.value.code == 4401


async def test_websocket_pushes_new_parent_command(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    await incoming.put({"type": "websocket.connect"})

    async def receive():
        return await incoming.get()

    async def send(message):
        await outgoing.put(message)

    socket = WebSocket(
        {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "wss",
            "path": "/api/device/ws",
            "raw_path": b"/api/device/ws",
            "query_string": b"",
            "headers": [(b"authorization", f"Bearer {tokens['access_token']}".encode())],
            "client": ("test", 1),
            "server": ("test.local", 443),
            "subprotocols": [],
            "state": {},
        },
        receive,
        send,
    )
    from app.modules.sync.router import device_socket

    task = asyncio.create_task(device_socket(socket))
    assert (await outgoing.get())["type"] == "websocket.accept"
    account = (await parent.get("/api/auth/me")).json()
    async with get_sessionmaker()() as db:
        await commands.create_command(
            db,
            tokens["device_id"],
            child["id"],
            account["id"],
            "lock",
            Actor(account_id=account["id"], ip="127.0.0.1"),
        )
    pushed = json.loads((await outgoing.get())["text"])
    assert pushed["command"]["type"] == "lock"
    await incoming.put(
        {
            "type": "websocket.receive",
            "text": json.dumps({"type": "ack", "id": pushed["command"]["id"]}),
        }
    )
    await asyncio.sleep(0.02)
    async with get_sessionmaker()() as db:
        listed = await commands.list_commands(db, tokens["device_id"], child["id"], account["id"])
    assert listed[0]["status"] == "acknowledged"
    await incoming.put({"type": "websocket.disconnect", "code": 1000})
    await task
