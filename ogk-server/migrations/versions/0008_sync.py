"""sync: events, event_batches, device_alerts

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-19 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(_in("type", EVENT_TYPES), name="ck_events_type"),
        sa.CheckConstraint("duration_sec BETWEEN 0 AND 86400", name="ck_events_duration_sec"),
        sa.CheckConstraint("policy_id >= 0", name="ck_events_policy_id"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_device_id", "events", ["device_id"])
    op.create_index("ix_events_child_id", "events", ["child_id"])
    op.create_table(
        "event_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "idempotency_key", name="uq_event_batches_device_key"),
    )
    op.create_table(
        "device_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.String(length=64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(_in("type", ALERT_TYPES), name="ck_device_alerts_type"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_alerts_device_id", "device_alerts", ["device_id"])
    op.create_index(
        "uq_device_alerts_open",
        "device_alerts",
        ["device_id", "type"],
        unique=True,
        sqlite_where=sa.text("resolved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_device_alerts_open", table_name="device_alerts")
    op.drop_index("ix_device_alerts_device_id", table_name="device_alerts")
    op.drop_table("device_alerts")
    op.drop_table("event_batches")
    op.drop_index("ix_events_child_id", table_name="events")
    op.drop_index("ix_events_device_id", table_name="events")
    op.drop_table("events")
