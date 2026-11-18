"""enrollment: pairing_codes, device_tokens, consent_records; devices gains token and revocation columns

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-18 14:00:00.000000

No API created devices before this revision, but rows inserted by hand would block NOT NULL columns,
so the new hash columns are added with an empty default that a table rebuild then drops.
Foreign keys are off during the rebuild, otherwise dropping the old devices table cascades to
windows_accounts (same reason as 0005). PRAGMA foreign_keys only works outside a transaction.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rebuild_devices(change) -> None:
    with op.get_context().autocommit_block():
        op.execute("PRAGMA foreign_keys=OFF")
    with op.batch_alter_table("devices", recreate="always") as batch_op:
        change(batch_op)
    with op.get_context().autocommit_block():
        op.execute("PRAGMA foreign_keys=ON")
    violations = op.get_bind().exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"Foreign key violations after rebuilding devices: {violations}")


def _add_device_columns(batch_op) -> None:
    batch_op.add_column(sa.Column("fingerprint_hash", sa.String(length=64), nullable=False, server_default=""))
    batch_op.add_column(sa.Column("secret_hash", sa.String(length=64), nullable=False, server_default=""))
    batch_op.add_column(sa.Column("revoked_at", sa.DateTime(), nullable=True))
    batch_op.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))


def _drop_device_defaults(batch_op) -> None:
    batch_op.alter_column("fingerprint_hash", server_default=None)
    batch_op.alter_column("secret_hash", server_default=None)


def _drop_device_columns(batch_op) -> None:
    batch_op.drop_column("last_seen_at")
    batch_op.drop_column("revoked_at")
    batch_op.drop_column("secret_hash")
    batch_op.drop_column("fingerprint_hash")


def upgrade() -> None:
    _rebuild_devices(_add_device_columns)
    _rebuild_devices(_drop_device_defaults)

    op.create_table(
        "pairing_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("consent_ip", sa.String(length=45), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("pairing_codes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_pairing_codes_owner_id"), ["owner_id"], unique=False)

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("kind IN ('access', 'refresh')", name="ck_device_tokens_kind"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("device_tokens", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_device_tokens_device_id"), ["device_id"], unique=False)

    op.create_table(
        "consent_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("consented_at", sa.DateTime(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("consent_version", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("consent_records", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_consent_records_account_id"), ["account_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_consent_records_device_id"), ["device_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("consent_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_consent_records_device_id"))
        batch_op.drop_index(batch_op.f("ix_consent_records_account_id"))
    op.drop_table("consent_records")
    with op.batch_alter_table("device_tokens", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_device_tokens_device_id"))
    op.drop_table("device_tokens")
    with op.batch_alter_table("pairing_codes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_pairing_codes_owner_id"))
    op.drop_table("pairing_codes")
    _rebuild_devices(_drop_device_columns)
