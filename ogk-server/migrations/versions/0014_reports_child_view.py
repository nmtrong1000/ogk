"""Daily screen time, child-view codes and sessions, report index on events.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("device_id", "child_id", "day", name="uq_daily_usage_device_child_day"),
        sa.CheckConstraint("seconds BETWEEN 0 AND 86400", name="ck_daily_usage_seconds"),
    )
    op.create_index("ix_daily_usage_device_id", "daily_usage", ["device_id"])
    op.create_index("ix_daily_usage_child_id_day", "daily_usage", ["child_id", "day"])
    op.create_table(
        "child_view_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_child_view_codes_device_id", "child_view_codes", ["device_id"])
    op.create_index("ix_child_view_codes_child_id", "child_view_codes", ["child_id"])
    op.create_table(
        "child_view_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_child_view_sessions_child_id", "child_view_sessions", ["child_id"])
    op.create_index("ix_child_view_sessions_device_id", "child_view_sessions", ["device_id"])
    op.create_index("ix_events_child_id_ts", "events", ["child_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_events_child_id_ts", table_name="events")
    op.drop_index("ix_child_view_sessions_device_id", table_name="child_view_sessions")
    op.drop_index("ix_child_view_sessions_child_id", table_name="child_view_sessions")
    op.drop_table("child_view_sessions")
    op.drop_index("ix_child_view_codes_child_id", table_name="child_view_codes")
    op.drop_index("ix_child_view_codes_device_id", table_name="child_view_codes")
    op.drop_table("child_view_codes")
    op.drop_index("ix_daily_usage_child_id_day", table_name="daily_usage")
    op.drop_index("ix_daily_usage_device_id", table_name="daily_usage")
    op.drop_table("daily_usage")
