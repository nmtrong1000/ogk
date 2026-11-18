"""family: children, devices, windows_accounts

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "children",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.LargeBinary(), nullable=False),
        sa.Column("birth_year", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("children", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_children_owner_id"), ["owner_id"], unique=False)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_devices_owner_id"), ["owner_id"], unique=False)

    op.create_table(
        "windows_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=True),
        sa.Column("sid", sa.String(length=184), nullable=False),
        sa.Column("username", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "sid", name="uq_windows_accounts_device_sid"),
    )
    with op.batch_alter_table("windows_accounts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_windows_accounts_child_id"), ["child_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_windows_accounts_device_id"), ["device_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("windows_accounts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_windows_accounts_device_id"))
        batch_op.drop_index(batch_op.f("ix_windows_accounts_child_id"))
    op.drop_table("windows_accounts")
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_devices_owner_id"))
    op.drop_table("devices")
    with op.batch_alter_table("children", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_children_owner_id"))
    op.drop_table("children")
