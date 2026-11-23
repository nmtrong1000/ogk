"""Parent commands delivered to enrolled devices.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parent_commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("type IN ('lock', 'unlock', 'add_time')", name="ck_parent_commands_type"),
        sa.CheckConstraint("status IN ('pending', 'acknowledged')", name="ck_parent_commands_status"),
        sa.CheckConstraint("minutes IN (0, 15)", name="ck_parent_commands_minutes"),
    )
    op.create_index("ix_parent_commands_device_id", "parent_commands", ["device_id"])
    op.create_index("ix_parent_commands_child_id", "parent_commands", ["child_id"])
    op.create_index("ix_parent_commands_actor_id", "parent_commands", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_parent_commands_actor_id", table_name="parent_commands")
    op.drop_index("ix_parent_commands_child_id", table_name="parent_commands")
    op.drop_index("ix_parent_commands_device_id", table_name="parent_commands")
    op.drop_table("parent_commands")
