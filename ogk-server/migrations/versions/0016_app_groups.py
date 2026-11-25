"""Application groups and daily budgets on policies and policy_versions.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_GROUPS = (
    '[{"budget_minutes":null,"id":"education","name":"Học tập"},'
    '{"budget_minutes":null,"id":"entertainment","name":"Giải trí"},'
    '{"budget_minutes":null,"id":"social","name":"Mạng xã hội"},'
    '{"budget_minutes":null,"id":"games","name":"Trò chơi"},'
    '{"budget_minutes":null,"id":"adult","name":"Người lớn"},'
    '{"budget_minutes":null,"id":"unclassified","name":"Chưa phân loại"}]'
)


def upgrade() -> None:
    for table in ("policies", "policy_versions"):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.add_column(sa.Column("app_groups", sa.Text(), nullable=False, server_default=DEFAULT_GROUPS))
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.alter_column("app_groups", server_default=None)
            batch.create_check_constraint(
                f"ck_{table}_app_groups", "json_valid(app_groups) AND json_type(app_groups) = 'array'"
            )


def downgrade() -> None:
    for table in ("policies", "policy_versions"):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_constraint(f"ck_{table}_app_groups", type_="check")
            batch.drop_column("app_groups")
