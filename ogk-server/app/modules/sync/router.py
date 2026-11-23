"""device_router lives under /api/device/, which main.py exempts from CSRF because the agent sends no cookies.
The events body is read raw so malformed batches return invalid_batch or invalid_event instead of FastAPI's 422.
"""

import asyncio

from fastapi import APIRouter, Depends, Header, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, get_sessionmaker
from app.core.errors import AppError
from app.core.security import hash_token
from app.modules.audit.service import Actor, current_actor
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.enrollment.models import TOKEN_ACCESS, DeviceToken
from app.modules.enrollment.service import current_device
from app.modules.family.models import Device
from app.modules.sync import commands, service
from app.modules.sync.schemas import AlertOut, EventsOut, HeartbeatIn, HeartbeatOut

router = APIRouter(prefix="/api/alerts", tags=["sync"], dependencies=[Depends(require_parent)])
device_router = APIRouter(tags=["device"])
command_router = APIRouter(prefix="/api", tags=["commands"], dependencies=[Depends(require_parent)])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    device_id: int | None = None, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)
):
    return await service.list_alerts(db, account.id, device_id)


@device_router.post("/api/device/heartbeat", response_model=HeartbeatOut)
async def heartbeat(body: HeartbeatIn, device: Device = Depends(current_device), db: AsyncSession = Depends(get_db)):
    return await service.heartbeat(db, device, body)


@device_router.post("/api/device/events", response_model=EventsOut)
async def post_events(
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    device: Device = Depends(current_device),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await request.json()
    except ValueError as exc:
        raise AppError(422, "invalid_batch") from exc
    return await service.receive_events(db, device, idempotency_key, payload)


@command_router.post("/devices/{device_id}/children/{child_id}/commands", status_code=201)
async def create_command(
    device_id: int,
    child_id: int,
    body: dict,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
):
    if not isinstance(body, dict) or set(body) != {"type"} or not isinstance(body["type"], str):
        raise AppError(422, "invalid_command")
    return await commands.create_command(db, device_id, child_id, account.id, body["type"], actor)


@command_router.get("/devices/{device_id}/children/{child_id}/commands")
async def list_commands(
    device_id: int,
    child_id: int,
    account: Account = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    return await commands.list_commands(db, device_id, child_id, account.id)


@device_router.post("/api/device/commands/{command_id}/ack")
async def acknowledge_command(
    command_id: int, device: Device = Depends(current_device), db: AsyncSession = Depends(get_db)
):
    return {"acknowledged": await commands.acknowledge(db, device.id, command_id)}


@device_router.websocket("/api/device/ws")
async def device_socket(websocket: WebSocket):
    header = websocket.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    async with get_sessionmaker()() as db:
        row = (
            await db.execute(
                select(DeviceToken).where(
                    DeviceToken.token_hash == hash_token(token),
                    DeviceToken.kind == TOKEN_ACCESS,
                    DeviceToken.revoked_at.is_(None),
                    DeviceToken.expires_at > service.now(),
                )
            )
        ).scalar_one_or_none()
        device = None if row is None else await db.get(Device, row.device_id)
        if device is None or device.revoked_at is not None:
            await websocket.close(code=4401)
            return
        device_id = device.id
        token_hash = row.token_hash
    await websocket.accept()
    queue = commands.subscribe(device_id)
    try:
        async with get_sessionmaker()() as db:
            initial = await commands.pending_commands(db, device_id)
        for command in initial:
            await websocket.send_json({"command": command})
        while True:
            message_task = asyncio.create_task(websocket.receive_json())
            command_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                (message_task, command_task), timeout=10, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if not done:
                await asyncio.gather(*pending, return_exceptions=True)
                async with get_sessionmaker()() as db:
                    current = (
                        await db.execute(
                            select(DeviceToken).where(
                                DeviceToken.token_hash == token_hash,
                                DeviceToken.revoked_at.is_(None),
                                DeviceToken.expires_at > service.now(),
                            )
                        )
                    ).scalar_one_or_none()
                    active_device = await db.get(Device, device_id)
                if current is None or active_device is None or active_device.revoked_at is not None:
                    await websocket.close(code=4401)
                    break
                await websocket.send_json({"ping": True})
                continue
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            if message_task in done:
                message = message_task.result()
                if isinstance(message, dict) and message.get("type") == "ack" and isinstance(message.get("id"), int):
                    async with get_sessionmaker()() as db:
                        await commands.acknowledge(db, device_id, message["id"])
            if command_task in done:
                await websocket.send_json({"command": command_task.result()})
    except WebSocketDisconnect:
        pass
    finally:
        commands.unsubscribe(device_id, queue)
