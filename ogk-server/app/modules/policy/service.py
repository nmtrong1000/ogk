"""A policy row is created lazily with defaults the first time a child's policy is read.
The version is bumped inside the UPDATE statement so two concurrent edits never share a version number.
issued_at is the row's updated_at, so the same version always signs to the same bytes.
"""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import signing
from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.audit import service as audit
from app.modules.family import service as family
from app.modules.family.models import Device
from app.modules.policy.models import DEFAULT_QUOTA_MINUTES, MAX_QUOTA_MINUTES, MIN_QUOTA_MINUTES, Policy

FORMAT = 1
AUDIT_TARGET = "policy"


def now() -> datetime:
    return utcnow()


def iso(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_quota(minutes: int) -> int:
    if not MIN_QUOTA_MINUTES <= minutes <= MAX_QUOTA_MINUTES:
        raise AppError(422, "invalid_quota")
    return minutes


def policy_out(policy: Policy) -> dict:
    return {
        "child_id": policy.child_id,
        "policy_version": policy.version,
        "daily_quota_minutes": policy.daily_quota_minutes,
        "updated_at": policy.updated_at,
    }


def document(policy: Policy) -> dict:
    return {
        "child_id": policy.child_id,
        "format": FORMAT,
        "issued_at": iso(policy.updated_at),
        "policy_version": policy.version,
        "rules": {"daily_quota_minutes": policy.daily_quota_minutes},
    }


def signed(policy: Policy) -> dict:
    doc = document(policy)
    return {"policy": doc, "signature": signing.sign(doc), "key_id": signing.signing_key_id()}


async def ensure_policies(db: AsyncSession, child_ids: list[int]) -> list[Policy]:
    if not child_ids:
        return []
    at = now()
    rows = [
        {"child_id": cid, "version": 1, "daily_quota_minutes": DEFAULT_QUOTA_MINUTES, "updated_at": at}
        for cid in child_ids
    ]
    await db.execute(insert(Policy).values(rows).on_conflict_do_nothing(index_elements=["child_id"]))
    await db.commit()
    stmt = select(Policy).where(Policy.child_id.in_(child_ids)).order_by(Policy.child_id)
    return list((await db.execute(stmt)).scalars())


async def get_policy(db: AsyncSession, child_id: int, owner_id: int) -> dict:
    child = await family.get_child_for_owner(db, child_id, owner_id)
    (policy,) = await ensure_policies(db, [child.id])
    return policy_out(policy)


async def update_policy(
    db: AsyncSession, child_id: int, owner_id: int, daily_quota_minutes: int, *, actor: audit.Actor
) -> dict:
    child = await family.get_child_for_owner(db, child_id, owner_id)
    minutes = validate_quota(daily_quota_minutes)
    (policy,) = await ensure_policies(db, [child.id])
    if policy.daily_quota_minutes == minutes:
        return policy_out(policy)
    old = {"daily_quota_minutes": policy.daily_quota_minutes, "policy_version": policy.version}
    stmt = (
        update(Policy)
        .where(Policy.child_id == child.id)
        .values(version=Policy.version + 1, daily_quota_minutes=minutes, updated_at=now())
        .returning(Policy.version)
        .execution_options(synchronize_session=False)
    )
    version = (await db.execute(stmt)).scalar_one()
    audit.record(
        db, actor, "update", AUDIT_TARGET, child.id, old, {"daily_quota_minutes": minutes, "policy_version": version}
    )
    await db.commit()
    await db.refresh(policy)
    return policy_out(policy)


async def device_policies(db: AsyncSession, device: Device) -> dict:
    child_ids = await family.child_ids_on_device(db, device.id)
    return {"policies": [signed(policy) for policy in await ensure_policies(db, child_ids)]}
