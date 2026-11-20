"""app_rules: per-child app allow/block rules on policies and policy_versions

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-19 12:00:00.000000

Existing rows start with an empty rule list. Batch mode reflects named CHECK constraints, so the ones on the
dropped column must be dropped first on downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECK = "json_valid(app_rules) AND json_type(app_rules) = 'array'"


def upgrade() -> None:
    for table in ("policies", "policy_versions"):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.add_column(sa.Column("app_rules", sa.Text(), nullable=False, server_default="[]"))
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.alter_column("app_rules", server_default=None)
            batch.create_check_constraint(f"ck_{table}_app_rules", CHECK)


def downgrade() -> None:
    for table in ("policies", "policy_versions"):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_constraint(f"ck_{table}_app_rules", type_="check")
            batch.drop_column("app_rules")
