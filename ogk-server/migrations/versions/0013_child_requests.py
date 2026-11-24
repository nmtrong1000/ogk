"""Child requests and parent decisions.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "child_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("type IN ('add_time', 'blocked_domain')", name="ck_child_requests_type"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_child_requests_status"),
    )
    op.create_index("ix_child_requests_device_id", "child_requests", ["device_id"])
    op.create_index("ix_child_requests_child_id", "child_requests", ["child_id"])
    op.create_index("ix_child_requests_status", "child_requests", ["status"])
    op.create_index("ix_child_requests_decided_by", "child_requests", ["decided_by"])


def downgrade() -> None:
    op.drop_index("ix_child_requests_decided_by", table_name="child_requests")
    op.drop_index("ix_child_requests_status", table_name="child_requests")
    op.drop_index("ix_child_requests_child_id", table_name="child_requests")
    op.drop_index("ix_child_requests_device_id", table_name="child_requests")
    op.drop_table("child_requests")
