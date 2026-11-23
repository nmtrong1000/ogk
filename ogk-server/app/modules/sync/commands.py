import asyncio
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.audit import service as audit
from app.modules.family.models import Child, Device, WindowsAccount
from app.modules.sync.models import COMMAND_TYPES, ParentCommand

_listeners: dict[int, set[asyncio.Queue]] = {}


async def publish(device_id: int, body: dict) -> None:
    for queue in tuple(_listeners.get(device_id, ())):
        await queue.put(body)


def subscribe(device_id: int) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _listeners.setdefault(device_id, set()).add(queue)
    return queue


def unsubscribe(device_id: int, queue: asyncio.Queue) -> None:
    listeners = _listeners.get(device_id)
    if listeners is not None:
        listeners.discard(queue)
        if not listeners:
            _listeners.pop(device_id, None)


def command_body(row: ParentCommand) -> dict:
    return {
        "id": row.id,
        "child_id": row.child_id,
        "type": row.type,
        "minutes": row.minutes,
        "status": row.status,
        "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
        "acknowledged_at": None
        if row.acknowledged_at is None
        else row.acknowledged_at.isoformat().replace("+00:00", "Z"),
    }


async def create_command(
    db: AsyncSession,
    device_id: int,
    child_id: int,
    owner_id: int,
    kind: str,
    actor: audit.Actor,
) -> dict:
    if kind not in COMMAND_TYPES:
        raise AppError(422, "invalid_command")
    device = (
        await db.execute(
            select(Device)
            .join(WindowsAccount, WindowsAccount.device_id == Device.id)
            .join(Child, Child.id == WindowsAccount.child_id)
            .where(
                Device.id == device_id,
                Device.owner_id == owner_id,
                Device.revoked_at.is_(None),
                Child.id == child_id,
                Child.owner_id == owner_id,
            )
        )
    ).scalar_one_or_none()
    if device is None:
        raise AppError(404, "not_found")
    at = utcnow()
    row = ParentCommand(
        device_id=device_id,
        child_id=child_id,
        actor_id=actor.account_id,
        type=kind,
        minutes=15 if kind == "add_time" else 0,
        status="pending",
        created_at=at,
    )
    db.add(row)
    await db.flush()
    audit.record(
        db,
        actor,
        "create",
        "parent_command",
        row.id,
        None,
        {"device_id": device_id, "child_id": child_id, "type": kind, "minutes": row.minutes},
    )
    await db.commit()
    body = command_body(row)
    await publish(device_id, body)
    return body


async def list_commands(db: AsyncSession, device_id: int, child_id: int, owner_id: int) -> list[dict]:
    assigned = (
        await db.execute(
            select(WindowsAccount.id)
            .join(Device, Device.id == WindowsAccount.device_id)
            .join(Child, Child.id == WindowsAccount.child_id)
            .where(
                Device.id == device_id,
                Device.owner_id == owner_id,
                Device.revoked_at.is_(None),
                Child.id == child_id,
                Child.owner_id == owner_id,
            )
        )
    ).scalar_one_or_none()
    if assigned is None:
        raise AppError(404, "not_found")
    rows = await db.execute(
        select(ParentCommand)
        .where(ParentCommand.device_id == device_id, ParentCommand.child_id == child_id)
        .order_by(ParentCommand.id.desc())
        .limit(20)
    )
    return [command_body(row) for row in rows.scalars()]


async def pending_commands(db: AsyncSession, device_id: int) -> list[dict]:
    rows = await db.execute(
        select(ParentCommand)
        .where(ParentCommand.device_id == device_id, ParentCommand.status == "pending")
        .order_by(ParentCommand.id)
    )
    return [command_body(row) for row in rows.scalars()]


async def acknowledge(db: AsyncSession, device_id: int, command_id: int) -> bool:
    at: datetime = utcnow()
    result = await db.execute(
        update(ParentCommand)
        .where(
            ParentCommand.id == command_id,
            ParentCommand.device_id == device_id,
            ParentCommand.status == "pending",
        )
        .values(status="acknowledged", acknowledged_at=at)
    )
    await db.commit()
    return result.rowcount == 1
