"""auth: accounts, sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17 22:05:19.962313

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("role IN ('parent', 'admin')", name="ck_accounts_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sessions_account_id"), ["account_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sessions_expires_at"), ["expires_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sessions_expires_at"))
        batch_op.drop_index(batch_op.f("ix_sessions_account_id"))
    op.drop_table("sessions")
    op.drop_table("accounts")
