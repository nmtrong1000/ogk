from datetime import UTC, date, datetime, timedelta

from app.core.db import get_sessionmaker
from app.modules.sync.models import ChildRequest, DailyUsage, DeviceAlert, Event, EventBatch, ParentCommand
from tests.sync.conftest import agent, other_parent

__all__ = ["agent", "other_parent"]

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
TODAY = date(2026, 11, 24)


async def seed_history(device_id: int, child_id: int, actor_id: int, age_days: int, tag: str) -> None:
    at = NOW - timedelta(days=age_days)
    async with get_sessionmaker()() as db:
        db.add_all(
            [
                Event(
                    ts=at,
                    device_id=device_id,
                    child_id=child_id,
                    type="app_start",
                    subject=f"{tag}.exe",
                    duration_sec=0,
                    policy_id=1,
                ),
                EventBatch(device_id=device_id, idempotency_key=f"key-{tag}", received_at=at, event_count=1),
                DeviceAlert(
                    device_id=device_id,
                    type="clock_tampered",
                    detail=tag,
                    first_seen_at=at,
                    last_seen_at=at,
                    resolved_at=at,
                ),
                ChildRequest(device_id=device_id, child_id=child_id, type="add_time", created_at=at),
                ParentCommand(device_id=device_id, child_id=child_id, actor_id=actor_id, type="lock", created_at=at),
                DailyUsage(
                    device_id=device_id,
                    child_id=child_id,
                    day=TODAY - timedelta(days=age_days),
                    seconds=60,
                    updated_at=at,
                ),
            ]
        )
        await db.commit()
