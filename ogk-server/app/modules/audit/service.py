"""record() does not commit: the caller commits the entry in the same transaction as the change.
now() is the module clock; tests replace it to simulate time.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import client_ip
from app.modules.audit.models import ACTIONS, AuditLog
from app.modules.auth import service as auth_service
from app.modules.auth.models import ROLE_ADMIN, Account

MAX_PAGE_SIZE = 100


def now() -> datetime:
    return utcnow()


@dataclass(frozen=True)
class Actor:
    account_id: int
    ip: str


async def current_actor(request: Request, account: Account = Depends(auth_service.current_user)) -> Actor:
    return Actor(account_id=account.id, ip=client_ip(request))


def _dump(value: dict[str, Any] | None) -> str | None:
    return None if value is None else json.dumps(value, ensure_ascii=False, sort_keys=True)


def record(
    db: AsyncSession,
    actor: Actor,
    action: str,
    target_type: str,
    target_id: int,
    old: dict[str, Any] | None,
    new: dict[str, Any] | None,
) -> AuditLog:
    if action not in ACTIONS:
        raise ValueError(f"invalid action: {action}")
    entry = AuditLog(
        actor_id=actor.account_id,
        at=now(),
        ip=actor.ip,
        action=action,
        target_type=target_type,
        target_id=target_id,
        old_value=_dump(old),
        new_value=_dump(new),
    )
    db.add(entry)
    return entry


async def list_logs(db: AsyncSession, viewer: Account, page: int, size: int) -> dict[str, Any]:
    if page < 1 or not 1 <= size <= MAX_PAGE_SIZE:
        raise AppError(422, "invalid_page")
    is_admin = viewer.role == ROLE_ADMIN
    stmt = select(AuditLog)
    count = select(func.count()).select_from(AuditLog)
    if not is_admin:
        stmt = stmt.where(AuditLog.actor_id == viewer.id)
        count = count.where(AuditLog.actor_id == viewer.id)
    total = (await db.execute(count)).scalar_one()
    rows = list(
        (
            await db.execute(
                stmt.order_by(AuditLog.at.desc(), AuditLog.id.desc()).offset((page - 1) * size).limit(size)
            )
        ).scalars()
    )
    emails = await auth_service.emails_by_ids(db, {r.actor_id for r in rows})
    items = [
        {
            "id": r.id,
            "at": r.at,
            "actor_id": r.actor_id,
            "actor_email": emails.get(r.actor_id),
            "ip": r.ip,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "old_value": None if is_admin or r.old_value is None else json.loads(r.old_value),
            "new_value": None if is_admin or r.new_value is None else json.loads(r.new_value),
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "size": size}
