"""events holds exactly the 7 fields of the event schema plus a surrogate id; device alerts live in
device_alerts so the events table keeps only the 9 required types.
uq_device_alerts_open is a partial index: at most one unresolved alert per (device, type).
parent_commands and child_requests use AUTOINCREMENT because the agent keys them by id, and the retention
purge would otherwise let SQLite hand a deleted id out again.
daily_usage.day is the agent's local day, not a UTC day: the agent counts screen time per local day and the
heartbeat repeats recent days, so each row is overwritten with the latest value.
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime

EVENT_TYPES = (
    "app_start",
    "app_stop",
    "domain_query",
    "blocked_app",
    "blocked_domain",
    "quota_warning",
    "locked",
    "unlock_request",
    "override_granted",
)
ALERT_TYPES = ("enforcement_disabled", "clock_tampered")
MAX_SUBJECT = 255
MAX_DURATION_SEC = 86400
MAX_IDEMPOTENCY_KEY = 64
MAX_ALERT_DETAIL = 64
PARENT_COMMAND_TYPES = ("lock", "unlock", "add_time")
COMMAND_TYPES = (*PARENT_COMMAND_TYPES, "purge_child")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(_in("type", EVENT_TYPES), name="ck_events_type"),
        CheckConstraint(f"duration_sec BETWEEN 0 AND {MAX_DURATION_SEC}", name="ck_events_duration_sec"),
        CheckConstraint("policy_id >= 0", name="ck_events_policy_id"),
        Index("ix_events_child_id_ts", "child_id", "ts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime())
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(MAX_SUBJECT))
    duration_sec: Mapped[int]
    policy_id: Mapped[int]


class EventBatch(Base):
    __tablename__ = "event_batches"
    __table_args__ = (UniqueConstraint("device_id", "idempotency_key", name="uq_event_batches_device_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    idempotency_key: Mapped[str] = mapped_column(String(MAX_IDEMPOTENCY_KEY))
    received_at: Mapped[datetime] = mapped_column(UTCDateTime())
    event_count: Mapped[int]


class DeviceAlert(Base):
    __tablename__ = "device_alerts"
    __table_args__ = (
        CheckConstraint(_in("type", ALERT_TYPES), name="ck_device_alerts_type"),
        Index(
            "uq_device_alerts_open",
            "device_id",
            "type",
            unique=True,
            sqlite_where=text("resolved_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str | None] = mapped_column(String(MAX_ALERT_DETAIL))
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime())
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime())
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class ParentCommand(Base):
    __tablename__ = "parent_commands"
    __table_args__ = (
        CheckConstraint(_in("type", COMMAND_TYPES), name="ck_parent_commands_type"),
        CheckConstraint("status IN ('pending', 'acknowledged')", name="ck_parent_commands_status"),
        CheckConstraint("minutes IN (0, 15)", name="ck_parent_commands_minutes"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))
    minutes: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class ChildRequest(Base):
    __tablename__ = "child_requests"
    __table_args__ = (
        CheckConstraint("type IN ('add_time', 'blocked_domain')", name="ck_child_requests_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_child_requests_status"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    domain: Mapped[str | None] = mapped_column(String(253))
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending", index=True)
    message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), index=True)


class DailyUsage(Base):
    __tablename__ = "daily_usage"
    __table_args__ = (
        UniqueConstraint("device_id", "child_id", "day", name="uq_daily_usage_device_child_day"),
        CheckConstraint(f"seconds BETWEEN 0 AND {MAX_DURATION_SEC}", name="ck_daily_usage_seconds"),
        Index("ix_daily_usage_child_id_day", "child_id", "day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    day: Mapped[date]
    seconds: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
