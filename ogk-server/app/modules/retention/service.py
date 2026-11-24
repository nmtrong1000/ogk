"""History older than RETENTION_DAYS is deleted by a daily task; audit_logs are append-only and never purged.
wipe_child keeps the child, the current policy and the Windows-account mapping so the device stays managed.
The purge_child commands are queued after the history delete so they are not deleted with it, and are
published to open WebSockets only after the commit.
Log lines go to uvicorn's error logger because the server configures no other logger, so they show in the
server output (docker logs) without extra setup.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_sessionmaker, utcnow
from app.modules.audit import service as audit
from app.modules.family import service as family
from app.modules.policy import service as policy
from app.modules.reports import service as reports
from app.modules.sync import commands
from app.modules.sync import service as sync

RETENTION_DAYS = 90
PURGE_INTERVAL_SECONDS = 24 * 60 * 60
AUDIT_TARGET = "child_data"

log = logging.getLogger("uvicorn.error")


def now() -> datetime:
    return utcnow()


def cutoffs(at: datetime) -> tuple[datetime, date]:
    local_day = at.astimezone(get_settings().report_zone).date()
    return at - timedelta(days=RETENTION_DAYS), local_day - timedelta(days=RETENTION_DAYS)


async def purge_expired(db: AsyncSession) -> dict[str, int]:
    cutoff, cutoff_day = cutoffs(now())
    counts = await sync.purge_before(db, cutoff, cutoff_day)
    await db.commit()
    return counts


async def wipe_child(db: AsyncSession, child_id: int, owner_id: int, actor: audit.Actor) -> dict:
    devices = await family.list_child_devices(db, child_id, owner_id)
    counts = await sync.delete_child_history(db, child_id)
    counts["policy_versions"] = await policy.delete_old_versions(db, child_id)
    counts["child_views"] = await reports.delete_child_views(db, child_id)
    queued = [await commands.queue_purge(db, d["id"], child_id, actor) for d in devices]
    audit.record(db, actor, "delete", AUDIT_TARGET, child_id, counts, {"devices_notified": len(queued)})
    await db.commit()
    for row in queued:
        await commands.publish(row.device_id, commands.command_body(row))
    return {"devices_notified": len(queued)}


async def run_daily() -> None:
    while True:
        try:
            async with get_sessionmaker()() as db:
                counts = await purge_expired(db)
            log.info("retention purge removed %s", counts)
        except Exception:
            log.exception("retention purge failed")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)
