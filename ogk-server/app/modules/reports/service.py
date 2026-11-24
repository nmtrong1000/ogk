"""Days and weeks are cut in OGK_REPORT_TZ for both the parent report and the child view, so both show the same
numbers. Screen time comes from daily_usage, whose day is the agent's local day; app and domain figures come
from events cut by the same zone, which only agree when the child's PC uses that zone too.
A child-view session ends early when its device is removed.
A child-view code is claimed with a conditional UPDATE, so two requests racing with one code cannot both win.
Unknown, used and expired codes all answer invalid_code so a caller learns nothing about which one it was.
"""

import json
import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import AppError
from app.core.security import hash_token, new_token
from app.modules.audit.models import AuditLog
from app.modules.family import service as family
from app.modules.family.models import Child, Device
from app.modules.policy import service as policy
from app.modules.reports.models import ChildViewCode, ChildViewSession
from app.modules.sync.models import ChildRequest, DailyUsage, Event
from app.modules.sync.requests import request_out

TOP_LIMIT = 10
MAX_RANGE_DAYS = 90
DEFAULT_RANGE_DAYS = 7
MAX_PAGE_SIZE = 100
CODE_TTL = timedelta(seconds=60)
SESSION_TTL = timedelta(minutes=30)
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
POLICY_TARGET = "policy"


def now() -> datetime:
    return utcnow()


def today() -> date:
    return now().astimezone(get_settings().report_zone).date()


def _utc_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=get_settings().report_zone).astimezone(UTC)


def resolve_range(start: date | None, end: date | None, days: int | None = None) -> tuple[date, date]:
    if days is not None and not 1 <= days <= MAX_RANGE_DAYS:
        raise AppError(422, "invalid_range")
    end = end or today()
    start = start or end - timedelta(days=(days or DEFAULT_RANGE_DAYS) - 1)
    if start > end or (end - start).days + 1 > MAX_RANGE_DAYS:
        raise AppError(422, "invalid_range")
    return start, end


def _check_page(page: int, size: int) -> None:
    if page < 1 or not 1 <= size <= MAX_PAGE_SIZE:
        raise AppError(422, "invalid_page")


async def _daily(db: AsyncSession, child_id: int, start: date, end: date) -> list[dict]:
    rows = await db.execute(
        select(DailyUsage.day, func.sum(DailyUsage.seconds))
        .where(DailyUsage.child_id == child_id, DailyUsage.day >= start, DailyUsage.day <= end)
        .group_by(DailyUsage.day)
    )
    totals = {day: int(seconds) for day, seconds in rows}
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return [{"date": day, "seconds": totals.get(day, 0)} for day in days]


def _weekly(daily: list[dict]) -> list[dict]:
    weeks: dict[date, int] = {}
    for item in daily:
        monday = item["date"] - timedelta(days=item["date"].weekday())
        weeks[monday] = weeks.get(monday, 0) + item["seconds"]
    return [{"week_start": monday, "seconds": seconds} for monday, seconds in sorted(weeks.items())]


def _in_range(child_id: int, start: date, end: date):
    return (
        Event.child_id == child_id,
        Event.ts >= _utc_start(start),
        Event.ts < _utc_start(end + timedelta(days=1)),
    )


async def _top_apps(db: AsyncSession, child_id: int, start: date, end: date) -> list[dict]:
    total = func.sum(Event.duration_sec).label("seconds")
    rows = await db.execute(
        select(Event.subject, total)
        .where(*_in_range(child_id, start, end), Event.type == "app_stop")
        .group_by(Event.subject)
        .order_by(total.desc(), Event.subject)
        .limit(TOP_LIMIT)
    )
    return [{"name": name, "seconds": int(seconds)} for name, seconds in rows]


async def _top_domains(db: AsyncSession, child_id: int, start: date, end: date) -> list[dict]:
    hits = func.count().label("count")
    rows = await db.execute(
        select(Event.subject, hits)
        .where(*_in_range(child_id, start, end), Event.type == "domain_query")
        .group_by(Event.subject)
        .order_by(hits.desc(), Event.subject)
        .limit(TOP_LIMIT)
    )
    return [{"domain": domain, "count": count} for domain, count in rows]


async def _blocked(db: AsyncSession, child_id: int, start: date, end: date) -> dict:
    rows = await db.execute(
        select(Event.type, func.count())
        .where(*_in_range(child_id, start, end), Event.type.in_(("blocked_app", "blocked_domain")))
        .group_by(Event.type)
    )
    counts = dict(rows.all())
    apps, domains = counts.get("blocked_app", 0), counts.get("blocked_domain", 0)
    return {"apps": apps, "domains": domains, "total": apps + domains}


async def _quota_today_sec(db: AsyncSession, child_id: int) -> int:
    (row,) = await policy.ensure_policies(db, [child_id])
    minutes = row.weekend_quota_minutes if today().weekday() >= 5 else row.weekday_quota_minutes
    return minutes * 60


async def build_report(db: AsyncSession, child_id: int, start: date, end: date) -> dict:
    daily = await _daily(db, child_id, start, end)
    return {
        "child_id": child_id,
        "from": start,
        "to": end,
        "time_zone": get_settings().report_tz,
        "daily": daily,
        "weekly": _weekly(daily),
        "total_seconds": sum(item["seconds"] for item in daily),
        "top_apps": await _top_apps(db, child_id, start, end),
        "top_domains": await _top_domains(db, child_id, start, end),
        "blocked": await _blocked(db, child_id, start, end),
        "quota_today_seconds": await _quota_today_sec(db, child_id),
    }


async def parent_report(
    db: AsyncSession, child_id: int, owner_id: int, start: date | None, end: date | None, days: int | None = None
) -> dict:
    child = await family.get_child_for_owner(db, child_id, owner_id)
    start, end = resolve_range(start, end, days)
    return await build_report(db, child.id, start, end)


async def parent_requests(db: AsyncSession, child_id: int, owner_id: int, page: int, size: int) -> dict:
    _check_page(page, size)
    child = await family.get_child_for_owner(db, child_id, owner_id)
    where = (
        ChildRequest.child_id == child.id,
        Device.owner_id == owner_id,
    )
    base = select(ChildRequest).join(Device, Device.id == ChildRequest.device_id).where(*where)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = await db.execute(
        base.order_by(ChildRequest.created_at.desc(), ChildRequest.id.desc()).offset((page - 1) * size).limit(size)
    )
    items = [request_out(row, child.name) for row in rows.scalars()]
    return {"items": items, "total": total, "page": page, "size": size}


def _changes(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = (set(old) | set(new)) - {"policy_version"}
    return {field: {"old": old.get(field), "new": new.get(field)} for field in sorted(fields)}


async def rule_log(db: AsyncSession, child_id: int, page: int, size: int) -> dict:
    _check_page(page, size)
    where = (AuditLog.target_type == POLICY_TARGET, AuditLog.target_id == child_id)
    total = (await db.execute(select(func.count()).select_from(AuditLog).where(*where))).scalar_one()
    rows = await db.execute(
        select(AuditLog)
        .where(*where)
        .order_by(AuditLog.at.desc(), AuditLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = []
    for entry in rows.scalars():
        old = json.loads(entry.old_value) if entry.old_value else {}
        new = json.loads(entry.new_value) if entry.new_value else {}
        items.append({"id": entry.id, "at": entry.at, "changes": _changes(old, new)})
    return {"items": items, "total": total, "page": page, "size": size}


async def register_code(db: AsyncSession, device: Device, child_id: int, code: str) -> dict:
    if not CODE_RE.fullmatch(code):
        raise AppError(422, "invalid_child_view_code")
    child = await db.get(Child, child_id)
    if (
        child is None
        or child.owner_id != device.owner_id
        or child_id not in await family.child_ids_on_device(db, device.id)
    ):
        raise AppError(404, "not_found")
    at = now()
    await db.execute(delete(ChildViewCode).where(ChildViewCode.expires_at <= at))
    row = ChildViewCode(
        code_hash=hash_token(code), device_id=device.id, child_id=child_id, created_at=at, expires_at=at + CODE_TTL
    )
    db.add(row)
    await db.commit()
    return {"expires_at": row.expires_at}


async def exchange_code(db: AsyncSession, code: str) -> str:
    at = now()
    if not CODE_RE.fullmatch(code):
        raise AppError(400, "invalid_code")
    claimed = await db.execute(
        update(ChildViewCode)
        .where(
            ChildViewCode.code_hash == hash_token(code),
            ChildViewCode.used_at.is_(None),
            ChildViewCode.expires_at > at,
        )
        .values(used_at=at)
        .returning(ChildViewCode.child_id, ChildViewCode.device_id)
        .execution_options(synchronize_session=False)
    )
    row = claimed.one_or_none()
    if row is None:
        await db.rollback()
        raise AppError(400, "invalid_code")
    child_id, device_id = row
    device = await db.get(Device, device_id)
    if device is None or device.revoked_at is not None:
        await db.commit()
        raise AppError(400, "invalid_code")
    token = new_token()
    await db.execute(delete(ChildViewSession).where(ChildViewSession.expires_at <= at))
    db.add(
        ChildViewSession(
            id=hash_token(token), child_id=child_id, device_id=device_id, created_at=at, expires_at=at + SESSION_TTL
        )
    )
    await db.commit()
    return token


async def child_for_session(db: AsyncSession, token: str) -> int | None:
    row = (
        await db.execute(
            select(ChildViewSession.child_id)
            .join(Device, Device.id == ChildViewSession.device_id)
            .where(
                ChildViewSession.id == hash_token(token),
                ChildViewSession.expires_at > now(),
                Device.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    return row


async def end_session(db: AsyncSession, token: str) -> None:
    await db.execute(delete(ChildViewSession).where(ChildViewSession.id == hash_token(token)))
    await db.commit()


async def child_profile(db: AsyncSession, child_id: int) -> dict:
    child = await db.get(Child, child_id)
    if child is None:
        raise AppError(401, "not_authenticated")
    return {"name": child.name}


async def child_today(db: AsyncSession, child_id: int) -> dict:
    day = today()
    return await build_report(db, child_id, day, day)
