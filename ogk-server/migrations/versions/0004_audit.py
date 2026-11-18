"""audit: audit_logs (append-only)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 10:00:00.000000

The trigger SQL is copied here instead of imported from app, so this migration never changes with the code.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NO_UPDATE_TRIGGER = (
    "CREATE TRIGGER audit_logs_no_update BEFORE UPDATE ON audit_logs "
    "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END"
)
NO_DELETE_TRIGGER = (
    "CREATE TRIGGER audit_logs_no_delete BEFORE DELETE ON audit_logs "
    "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END"
)


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("old_value", sa.LargeBinary(), nullable=True),
        sa.Column("new_value", sa.LargeBinary(), nullable=True),
        sa.CheckConstraint("action IN ('create', 'update', 'delete')", name="ck_audit_logs_action"),
        sa.ForeignKeyConstraint(["actor_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_audit_logs_actor_id"), ["actor_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_audit_logs_at"), ["at"], unique=False)
    op.execute(NO_UPDATE_TRIGGER)
    op.execute(NO_DELETE_TRIGGER)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update")
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_audit_logs_at"))
        batch_op.drop_index(batch_op.f("ix_audit_logs_actor_id"))
    op.drop_table("audit_logs")
