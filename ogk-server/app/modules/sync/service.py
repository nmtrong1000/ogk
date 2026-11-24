"""A batch's idempotency key and its events are inserted in one transaction, so a batch is either stored once
with its key or not at all; a resent batch whose key is already stored is acknowledged without storing anything.
A child_id is accepted when the child belongs to the device's owner, not only when it is mapped right now,
because the agent may deliver events buffered before an account was reassigned.
"""

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.family import service as family
from app.modules.family.models import Child, Device
from app.modules.policy import service as policy
from app.modules.sync import commands, requests
from app.modules.sync.models import (
    EVENT_TYPES,
    MAX_DURATION_SEC,
    MAX_IDEMPOTENCY_KEY,
    MAX_SUBJECT,
    DeviceAlert,
    Event,
    EventBatch,
)
from app.modules.sync.schemas import HeartbeatIn

EVENT_FIELDS = ("ts", "device_id", "child_id", "type", "subject", "duration_sec", "policy_id")
DOMAIN_TYPES = ("domain_query", "blocked_domain")
MAX_BATCH = 500
MAX_ALERTS = 200
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TS_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
KEY_PATTERN = re.compile(rf"[A-Za-z0-9_-]{{1,{MAX_IDEMPOTENCY_KEY}}}")
DOMAIN_PATTERN = re.compile(
    r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


def now() -> datetime:
    return utcnow()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not TS_PATTERN.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, TS_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def _subject_ok(event_type: str, subject: Any) -> bool:
    if not isinstance(subject, str) or len(subject) > MAX_SUBJECT or "/" in subject or "\\" in subject:
        return False
    if event_type in DOMAIN_TYPES:
        return DOMAIN_PATTERN.fullmatch(subject) is not None
    return True


def _invalid(index: int, field: str | None) -> AppError:
    return AppError(422, "invalid_event", index=index, field=field)


def parse_event(raw: Any, index: int, device_id: int, child_ids: set[int]) -> dict:
    if not isinstance(raw, dict):
        raise _invalid(index, None)
    for key in raw:
        if key not in EVENT_FIELDS:
            raise _invalid(index, key)
    for key in EVENT_FIELDS:
        if key not in raw:
            raise _invalid(index, key)
    ts = _parse_ts(raw["ts"])
    if ts is None:
        raise _invalid(index, "ts")
    if raw["device_id"] != device_id or not _is_int(raw["device_id"]):
        raise _invalid(index, "device_id")
    if not _is_int(raw["child_id"]) or raw["child_id"] not in child_ids:
        raise _invalid(index, "child_id")
    if raw["type"] not in EVENT_TYPES:
        raise _invalid(index, "type")
    if not _subject_ok(raw["type"], raw["subject"]):
        raise _invalid(index, "subject")
    if not _is_int(raw["duration_sec"]) or not 0 <= raw["duration_sec"] <= MAX_DURATION_SEC:
        raise _invalid(index, "duration_sec")
    if not _is_int(raw["policy_id"]) or raw["policy_id"] < 0:
        raise _invalid(index, "policy_id")
    return {**raw, "ts": ts}


def validate_key(key: str | None) -> str:
    if key is None or not KEY_PATTERN.fullmatch(key):
        raise AppError(400, "invalid_idempotency_key")
    return key


def validate_batch(payload: Any) -> list:
    if not isinstance(payload, dict) or set(payload) != {"events"}:
        raise AppError(422, "invalid_batch")
    events = payload["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= MAX_BATCH:
        raise AppError(422, "invalid_batch")
    return events


async def _owner_child_ids(db: AsyncSession, owner_id: int) -> set[int]:
    return set((await db.execute(select(Child.id).where(Child.owner_id == owner_id))).scalars())


async def _batch_seen(db: AsyncSession, device_id: int, key: str) -> bool:
    stmt = select(EventBatch.id).where(EventBatch.device_id == device_id, EventBatch.idempotency_key == key)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def receive_events(db: AsyncSession, device: Device, key: str | None, payload: Any) -> dict:
    key = validate_key(key)
    if await _batch_seen(db, device.id, key):
        return {"accepted": 0, "duplicate": True}
    raw_events = validate_batch(payload)
    child_ids = await _owner_child_ids(db, device.owner_id)
    events = [parse_event(raw, i, device.id, child_ids) for i, raw in enumerate(raw_events)]
    db.add(EventBatch(device_id=device.id, idempotency_key=key, received_at=now(), event_count=len(events)))
    db.add_all(Event(**event) for event in events)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if await _batch_seen(db, device.id, key):
            return {"accepted": 0, "duplicate": True}
        raise
    return {"accepted": len(events), "duplicate": False}


async def _sync_alerts(db: AsyncSession, device_id: int, body: HeartbeatIn, at: datetime) -> None:
    reported = {}
    for alert in body.alerts:
        reported.setdefault(alert.type, alert)
    stmt = select(DeviceAlert).where(DeviceAlert.device_id == device_id, DeviceAlert.resolved_at.is_(None))
    for open_alert in (await db.execute(stmt)).scalars():
        alert = reported.pop(open_alert.type, None)
        if alert is None:
            open_alert.resolved_at = at
        else:
            open_alert.last_seen_at = at
            open_alert.detail = alert.detail
    for alert in reported.values():
        db.add(
            DeviceAlert(
                device_id=device_id,
                type=alert.type,
                detail=alert.detail,
                first_seen_at=min(alert.ts.astimezone(UTC), at),
                last_seen_at=at,
            )
        )


async def heartbeat(db: AsyncSession, device: Device, body: HeartbeatIn) -> dict:
    at = now()
    await _sync_alerts(db, device.id, body, at)
    await db.commit()
    policies = await policy.ensure_policies(db, await family.child_ids_on_device(db, device.id))
    return {
        "policy_versions": {str(p.child_id): p.version for p in policies},
        "commands": await commands.pending_commands(db, device.id),
        "requests": await requests.decided_for_device(db, device.id),
        "server_time": policy.iso(at),
    }


async def list_alerts(db: AsyncSession, owner_id: int, device_id: int | None) -> list[dict]:
    stmt = (
        select(DeviceAlert, Device.name)
        .join(Device, Device.id == DeviceAlert.device_id)
        .where(Device.owner_id == owner_id, Device.revoked_at.is_(None))
        .order_by(DeviceAlert.last_seen_at.desc(), DeviceAlert.id.desc())
        .limit(MAX_ALERTS)
    )
    if device_id is not None:
        await family.get_active_device_for_owner(db, device_id, owner_id)
        stmt = stmt.where(DeviceAlert.device_id == device_id)
    return [
        {
            "id": alert.id,
            "device_id": alert.device_id,
            "device_name": name,
            "type": alert.type,
            "detail": alert.detail,
            "first_seen_at": alert.first_seen_at,
            "last_seen_at": alert.last_seen_at,
            "resolved_at": alert.resolved_at,
        }
        for alert, name in (await db.execute(stmt)).all()
    ]
