import json
import re

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.audit import service as audit
from app.modules.family.models import Child, Device, WindowsAccount
from app.modules.policy import service as policy
from app.modules.sync import commands
from app.modules.sync.models import ChildRequest, ParentCommand

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def request_out(row: ChildRequest, child_name: str | None = None) -> dict:
    return {
        "id": row.id,
        "device_id": row.device_id,
        "child_id": row.child_id,
        "child_name": child_name,
        "type": row.type,
        "domain": row.domain,
        "status": row.status,
        "message": row.message,
        "created_at": row.created_at,
        "decided_at": row.decided_at,
    }


async def create(db: AsyncSession, device: Device, child_id: int, kind: str, domain: str | None) -> dict:
    assigned = await db.execute(
        select(WindowsAccount.id)
        .join(Child, Child.id == WindowsAccount.child_id)
        .where(WindowsAccount.device_id == device.id, Child.id == child_id, Child.owner_id == device.owner_id)
    )
    if assigned.scalar_one_or_none() is None:
        raise AppError(404, "not_found")
    if kind not in {"add_time", "blocked_domain"}:
        raise AppError(422, "invalid_request_type")
    if kind == "blocked_domain":
        domain = (domain or "").strip().rstrip(".").lower()
        if not DOMAIN_RE.fullmatch(domain):
            raise AppError(422, "invalid_domain")
    elif domain is not None:
        raise AppError(422, "invalid_request")
    row = ChildRequest(device_id=device.id, child_id=child_id, type=kind, domain=domain, created_at=utcnow())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return request_out(row)


async def list_for_parent(db: AsyncSession, owner_id: int, status: str | None) -> list[dict]:
    stmt = (
        select(ChildRequest, Child.name)
        .join(Child, Child.id == ChildRequest.child_id)
        .join(Device, Device.id == ChildRequest.device_id)
        .where(Child.owner_id == owner_id, Device.owner_id == owner_id)
        .order_by(ChildRequest.created_at.desc(), ChildRequest.id.desc())
        .limit(200)
    )
    if status is not None:
        if status not in {"pending", "approved", "rejected"}:
            raise AppError(422, "invalid_request_status")
        stmt = stmt.where(ChildRequest.status == status)
    return [request_out(row, name) for row, name in (await db.execute(stmt)).all()]


async def decision(
    db: AsyncSession, request_id: int, owner_id: int, approve: bool, message: str | None, actor: audit.Actor
) -> dict:
    row = (
        await db.execute(
            select(ChildRequest)
            .join(Child, Child.id == ChildRequest.child_id)
            .where(ChildRequest.id == request_id, Child.owner_id == owner_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppError(404, "not_found")
    if row.status != "pending":
        raise AppError(409, "request_already_decided")
    message = None if message is None else message.strip()
    if message == "":
        message = None
    if message is not None and len(message) > 500:
        raise AppError(422, "invalid_message")
    current_policy = None
    allowlist = None
    if approve and row.type == "blocked_domain":
        (current_policy,) = await policy.ensure_policies(db, [row.child_id])
        allowlist = json.loads(current_policy.web_allowlist)
    at = utcnow()
    status = "approved" if approve else "rejected"
    claimed = await db.execute(
        update(ChildRequest)
        .where(ChildRequest.id == row.id, ChildRequest.status == "pending")
        .values(
            status=status,
            message=message,
            decided_at=at,
            decided_by=actor.account_id,
        )
        .returning(ChildRequest.id)
    )
    if claimed.scalar_one_or_none() is None:
        await db.rollback()
        raise AppError(409, "request_already_decided")
    row = await db.get(ChildRequest, request_id)
    command_body = None
    old = {"status": "pending"}
    new = {"status": status, "message": message, "type": row.type, "domain": row.domain}
    audit.record(db, actor, "update", "child_request", row.id, old, new)
    if approve and row.type == "add_time":
        command_row = ParentCommand(
            device_id=row.device_id,
            child_id=row.child_id,
            actor_id=actor.account_id,
            type="add_time",
            minutes=15,
            status="pending",
            created_at=at,
        )
        db.add(command_row)
        await db.flush()
        command_body = commands.command_body(command_row)
    elif approve and row.type == "blocked_domain" and row.domain not in allowlist:
        old_policy = {"web_allowlist": allowlist, "policy_version": current_policy.version}
        updated = await policy._bump(
            db,
            row.child_id,
            {"web_allowlist": policy.validate_domain_rules([*allowlist, row.domain])},
            actor,
        )
        audit.record(
            db,
            actor,
            "update",
            "policy",
            row.child_id,
            old_policy,
            {"web_allowlist": json.loads(updated.web_allowlist), "policy_version": updated.version},
        )
    await db.commit()
    await db.refresh(row)
    if command_body is not None:
        await commands.publish(row.device_id, command_body)
    return request_out(row)


async def decided_for_device(db: AsyncSession, device_id: int) -> list[dict]:
    rows = await db.execute(
        select(ChildRequest)
        .where(ChildRequest.device_id == device_id, ChildRequest.status.in_(("approved", "rejected")))
        .order_by(ChildRequest.id.desc())
        .limit(20)
    )
    return [request_out(row) for row in rows.scalars()]
