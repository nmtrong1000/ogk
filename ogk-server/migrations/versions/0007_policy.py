"""policy: policies (one signed policy per child)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18 18:00:00.000000

No rows are backfilled: the service creates a child's policy with defaults the first time it is read.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("daily_quota_minutes", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_policies_version"),
        sa.CheckConstraint("daily_quota_minutes BETWEEN 0 AND 1440", name="ck_policies_daily_quota_minutes"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("child_id"),
    )


def downgrade() -> None:
    op.drop_table("policies")
