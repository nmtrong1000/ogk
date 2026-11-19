"""Names are encrypted in the DB and cannot be ORDER BY'd, so the list is sorted after decryption.
create flushes to get the child id, then the child and its audit entry commit in one transaction.
An update that changes nothing writes no audit entry and keeps updated_at.
create_device and revoke_device do not commit: enrollment commits them together with tokens and consent.
A revoked device is hidden from every parent query, so it behaves as removed.
assign_account bumps the policy of every child it touches because signed policies carry the child's SIDs;
policy imports this module, so the policy service is imported inside the function.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_owned, select_owned, utcnow
from app.core.errors import AppError
from app.modules.audit import service as audit
from app.modules.family.models import Child, Device, WindowsAccount

MAX_NAME_LENGTH = 64
MIN_BIRTH_YEAR = 2000
AUDIT_TARGET = "child"
AUDIT_DEVICE = "device"
AUDIT_WINDOWS_ACCOUNT = "windows_account"
MAX_DEVICE_NAME_LENGTH = 64


@dataclass(frozen=True)
class NewWindowsAccount:
    sid: str
    username: str


def now() -> datetime:
    return utcnow()


def snapshot(child: Child) -> dict:
    return {"name": child.name, "birth_year": child.birth_year}


def validate_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise AppError(422, "invalid_name")
    return name


def validate_birth_year(birth_year: int) -> int:
    if not MIN_BIRTH_YEAR <= birth_year <= now().year:
        raise AppError(422, "invalid_birth_year")
    return birth_year


async def list_children(db: AsyncSession, owner_id: int) -> list[Child]:
    children = list((await db.execute(select_owned(Child, owner_id))).scalars())
    return sorted(children, key=lambda c: (c.name.casefold(), c.id))


async def get_child_for_owner(db: AsyncSession, child_id: int, owner_id: int) -> Child:
    child = await get_owned(db, Child, child_id, owner_id)
    if child is None:
        raise AppError(404, "not_found")
    return child


async def create_child(db: AsyncSession, owner_id: int, name: str, birth_year: int, *, actor: audit.Actor) -> Child:
    at = now()
    child = Child(
        owner_id=owner_id,
        name=validate_name(name),
        birth_year=validate_birth_year(birth_year),
        created_at=at,
        updated_at=at,
    )
    db.add(child)
    await db.flush()
    audit.record(db, actor, "create", AUDIT_TARGET, child.id, None, snapshot(child))
    await db.commit()
    return child


async def update_child(
    db: AsyncSession,
    child_id: int,
    owner_id: int,
    name: str | None = None,
    birth_year: int | None = None,
    *,
    actor: audit.Actor,
) -> Child:
    child = await get_child_for_owner(db, child_id, owner_id)
    before = snapshot(child)
    if name is not None:
        child.name = validate_name(name)
    if birth_year is not None:
        child.birth_year = validate_birth_year(birth_year)
    after = snapshot(child)
    changed = [key for key in before if before[key] != after[key]]
    if not changed:
        return child
    child.updated_at = now()
    audit.record(
        db,
        actor,
        "update",
        AUDIT_TARGET,
        child.id,
        {key: before[key] for key in changed},
        {key: after[key] for key in changed},
    )
    await db.commit()
    return child


async def delete_child(db: AsyncSession, child_id: int, owner_id: int, *, actor: audit.Actor) -> None:
    child = await get_child_for_owner(db, child_id, owner_id)
    audit.record(db, actor, "delete", AUDIT_TARGET, child.id, snapshot(child), None)
    await db.delete(child)
    await db.commit()


def _device_out(device: Device, accounts: list[WindowsAccount]) -> dict:
    return {
        "id": device.id,
        "name": device.name,
        "created_at": device.created_at,
        "last_seen_at": device.last_seen_at,
        "accounts": sorted(accounts, key=lambda a: (a.username.casefold(), a.id)),
    }


async def _with_accounts(db: AsyncSession, devices: list[Device]) -> list[dict]:
    if not devices:
        return []
    ids = [d.id for d in devices]
    rows = (await db.execute(select(WindowsAccount).where(WindowsAccount.device_id.in_(ids)))).scalars()
    by_device: dict[int, list[WindowsAccount]] = {i: [] for i in ids}
    for account in rows:
        by_device[account.device_id].append(account)
    return [_device_out(d, by_device[d.id]) for d in sorted(devices, key=lambda d: (d.created_at, d.id))]


def _active_devices(owner_id: int):
    return select_owned(Device, owner_id).where(Device.revoked_at.is_(None))


async def list_devices(db: AsyncSession, owner_id: int) -> list[dict]:
    return await _with_accounts(db, list((await db.execute(_active_devices(owner_id))).scalars()))


async def list_child_devices(db: AsyncSession, child_id: int, owner_id: int) -> list[dict]:
    await get_child_for_owner(db, child_id, owner_id)
    stmt = _active_devices(owner_id).where(
        Device.id.in_(select(WindowsAccount.device_id).where(WindowsAccount.child_id == child_id))
    )
    return await _with_accounts(db, list((await db.execute(stmt)).scalars()))


async def get_active_device_for_owner(db: AsyncSession, device_id: int, owner_id: int) -> Device:
    device = (await db.execute(_active_devices(owner_id).where(Device.id == device_id))).scalar_one_or_none()
    if device is None:
        raise AppError(404, "not_found")
    return device


async def get_device(db: AsyncSession, device_id: int) -> Device | None:
    return await db.get(Device, device_id)


async def sids_by_child_on_device(db: AsyncSession, device_id: int) -> dict[int, list[str]]:
    stmt = select(WindowsAccount.child_id, WindowsAccount.sid).where(
        WindowsAccount.device_id == device_id, WindowsAccount.child_id.is_not(None)
    )
    result: dict[int, list[str]] = {}
    for child_id, sid in await db.execute(stmt):
        result.setdefault(child_id, []).append(sid)
    return {child_id: sorted(sids) for child_id, sids in result.items()}


async def owner_ids(db: AsyncSession, child_ids: list[int]) -> dict[int, int]:
    if not child_ids:
        return {}
    rows = await db.execute(select(Child.id, Child.owner_id).where(Child.id.in_(child_ids)))
    return {child_id: owner_id for child_id, owner_id in rows}


async def child_ids_on_device(db: AsyncSession, device_id: int) -> list[int]:
    stmt = (
        select(WindowsAccount.child_id)
        .where(WindowsAccount.device_id == device_id, WindowsAccount.child_id.is_not(None))
        .distinct()
        .order_by(WindowsAccount.child_id)
    )
    return list((await db.execute(stmt)).scalars())


def device_name(name: str) -> str:
    name = name.strip()[:MAX_DEVICE_NAME_LENGTH]
    return name or "Windows PC"


async def create_device(
    db: AsyncSession,
    owner_id: int,
    name: str,
    fingerprint_hash: str,
    secret_hash: str,
    accounts: list[NewWindowsAccount],
    *,
    actor: audit.Actor,
) -> Device:
    device = Device(
        owner_id=owner_id,
        name=device_name(name),
        created_at=now(),
        fingerprint_hash=fingerprint_hash,
        secret_hash=secret_hash,
    )
    db.add(device)
    await db.flush()
    seen: set[str] = set()
    for account in accounts:
        if account.sid in seen:
            continue
        seen.add(account.sid)
        db.add(WindowsAccount(device_id=device.id, child_id=None, sid=account.sid, username=account.username))
    audit.record(db, actor, "create", AUDIT_DEVICE, device.id, None, {"name": device.name})
    return device


async def revoke_device(db: AsyncSession, device_id: int, owner_id: int, *, actor: audit.Actor) -> Device:
    device = await get_active_device_for_owner(db, device_id, owner_id)
    device.revoked_at = now()
    audit.record(db, actor, "delete", AUDIT_DEVICE, device.id, {"name": device.name}, None)
    return device


async def assign_account(
    db: AsyncSession, device_id: int, account_id: int, child_id: int | None, owner_id: int, *, actor: audit.Actor
) -> WindowsAccount:
    await get_active_device_for_owner(db, device_id, owner_id)
    account = await db.get(WindowsAccount, account_id)
    if account is None or account.device_id != device_id:
        raise AppError(404, "not_found")
    if child_id is not None and await get_owned(db, Child, child_id, owner_id) is None:
        raise AppError(404, "child_not_found")
    if account.child_id == child_id:
        return account
    old = account.child_id
    account.child_id = child_id
    audit.record(db, actor, "update", AUDIT_WINDOWS_ACCOUNT, account.id, {"child_id": old}, {"child_id": child_id})
    from app.modules.policy import service as policy

    await policy.bump_for_accounts(db, [c for c in (old, child_id) if c is not None], actor=actor)
    await db.commit()
    return account
