"""screentime: weekday/weekend quotas, weekly schedule and policy_versions

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-19 09:00:00.000000

Both quotas start from the old daily quota and the schedule starts at the default 07:00-21:00 every day.
Each existing policy gets one policy_versions row for its current version, so history is never empty.
Batch mode reflects named CHECK constraints, so the one on a dropped column must be dropped first.
Downgrade keeps the weekday quota as the daily quota and drops the history.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_SCHEDULE = ("0" * 14 + "1" * 28 + "0" * 6) * 7


def upgrade() -> None:
    with op.batch_alter_table("policies", recreate="always") as batch:
        batch.add_column(sa.Column("weekday_quota_minutes", sa.Integer(), nullable=False, server_default="120"))
        batch.add_column(sa.Column("weekend_quota_minutes", sa.Integer(), nullable=False, server_default="120"))
        batch.add_column(sa.Column("weekly_schedule", sa.String(336), nullable=False, server_default=DEFAULT_SCHEDULE))
        batch.add_column(sa.Column("updated_by", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE policies SET weekday_quota_minutes = daily_quota_minutes, "
        "weekend_quota_minutes = daily_quota_minutes, "
        "updated_by = (SELECT owner_id FROM children WHERE children.id = policies.child_id)"
    )
    with op.batch_alter_table("policies", recreate="always") as batch:
        batch.drop_constraint("ck_policies_daily_quota_minutes", type_="check")
        batch.drop_column("daily_quota_minutes")
        batch.alter_column("weekday_quota_minutes", server_default=None)
        batch.alter_column("weekend_quota_minutes", server_default=None)
        batch.alter_column("weekly_schedule", server_default=None)
        batch.create_foreign_key("fk_policies_updated_by", "accounts", ["updated_by"], ["id"], ondelete="SET NULL")
        batch.create_check_constraint("ck_policies_weekday_quota_minutes", "weekday_quota_minutes BETWEEN 0 AND 1440")
        batch.create_check_constraint("ck_policies_weekend_quota_minutes", "weekend_quota_minutes BETWEEN 0 AND 1440")
        batch.create_check_constraint("ck_policies_weekly_schedule", "length(weekly_schedule) = 336")

    op.create_table(
        "policy_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("weekday_quota_minutes", sa.Integer(), nullable=False),
        sa.Column("weekend_quota_minutes", sa.Integer(), nullable=False),
        sa.Column("weekly_schedule", sa.String(336), nullable=False),
        sa.Column("set_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_policy_versions_version"),
        sa.CheckConstraint("weekday_quota_minutes BETWEEN 0 AND 1440", name="ck_policy_versions_weekday_quota_minutes"),
        sa.CheckConstraint("weekend_quota_minutes BETWEEN 0 AND 1440", name="ck_policy_versions_weekend_quota_minutes"),
        sa.CheckConstraint("length(weekly_schedule) = 336", name="ck_policy_versions_weekly_schedule"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_by"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_id", "version", name="uq_policy_versions_child_version"),
    )
    op.create_index("ix_policy_versions_child_id", "policy_versions", ["child_id"])
    op.execute(
        "INSERT INTO policy_versions (child_id, version, weekday_quota_minutes, weekend_quota_minutes, "
        "weekly_schedule, set_by, created_at) SELECT child_id, version, weekday_quota_minutes, "
        "weekend_quota_minutes, weekly_schedule, updated_by, updated_at FROM policies"
    )


def downgrade() -> None:
    op.drop_index("ix_policy_versions_child_id", table_name="policy_versions")
    op.drop_table("policy_versions")
    with op.batch_alter_table("policies", recreate="always") as batch:
        batch.add_column(sa.Column("daily_quota_minutes", sa.Integer(), nullable=False, server_default="120"))
    op.execute("UPDATE policies SET daily_quota_minutes = weekday_quota_minutes")
    with op.batch_alter_table("policies", recreate="always") as batch:
        for name in ("weekday_quota_minutes", "weekend_quota_minutes", "weekly_schedule"):
            batch.drop_constraint(f"ck_policies_{name}", type_="check")
        batch.drop_constraint("fk_policies_updated_by", type_="foreignkey")
        batch.drop_column("weekday_quota_minutes")
        batch.drop_column("weekend_quota_minutes")
        batch.drop_column("weekly_schedule")
        batch.drop_column("updated_by")
        batch.alter_column("daily_quota_minutes", server_default=None)
        batch.create_check_constraint("ck_policies_daily_quota_minutes", "daily_quota_minutes BETWEEN 0 AND 1440")
