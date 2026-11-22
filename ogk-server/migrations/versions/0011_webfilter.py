"""Per child web filtering rules and the editable shared classification catalog.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-22 00:00:00.000000
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.modules.webfilter.catalog_data import catalog_rows

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("policies", "policy_versions"):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.add_column(sa.Column("web_allowlist", sa.Text(), nullable=False, server_default="[]"))
            batch.add_column(sa.Column("web_blocklist", sa.Text(), nullable=False, server_default="[]"))
            batch.add_column(
                sa.Column("blocked_categories", sa.Text(), nullable=False, server_default='["adult","social"]')
            )
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.alter_column("web_allowlist", server_default=None)
            batch.alter_column("web_blocklist", server_default=None)
            batch.alter_column("blocked_categories", server_default=None)
            batch.create_check_constraint(
                f"ck_{table}_web_allowlist", "json_valid(web_allowlist) AND json_type(web_allowlist) = 'array'"
            )
            batch.create_check_constraint(
                f"ck_{table}_web_blocklist", "json_valid(web_blocklist) AND json_type(web_blocklist) = 'array'"
            )
            batch.create_check_constraint(
                f"ck_{table}_blocked_categories",
                "json_valid(blocked_categories) AND json_type(blocked_categories) = 'array'",
            )
    op.create_table(
        "web_categories",
        sa.Column("domain", sa.String(length=253), primary_key=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "category IN ('education', 'entertainment', 'social', 'games', 'adult', 'unclassified')",
            name="ck_web_categories_category",
        ),
    )
    op.create_index("ix_web_categories_category", "web_categories", ["category"])
    at = datetime.now(UTC).replace(tzinfo=None)
    op.bulk_insert(
        sa.table("web_categories", sa.column("domain"), sa.column("category"), sa.column("updated_at")),
        [{"domain": domain, "category": category, "updated_at": at} for domain, category in catalog_rows()],
    )
    bind = op.get_bind()
    policies = sa.table(
        "policies",
        sa.column("child_id"),
        sa.column("version"),
        sa.column("weekday_quota_minutes"),
        sa.column("weekend_quota_minutes"),
        sa.column("weekly_schedule"),
        sa.column("app_rules"),
        sa.column("web_allowlist"),
        sa.column("web_blocklist"),
        sa.column("blocked_categories"),
        sa.column("updated_by"),
        sa.column("updated_at"),
    )
    history = sa.table(
        "policy_versions",
        sa.column("id"),
        sa.column("child_id"),
        sa.column("version"),
        sa.column("weekday_quota_minutes"),
        sa.column("weekend_quota_minutes"),
        sa.column("weekly_schedule"),
        sa.column("app_rules"),
        sa.column("web_allowlist"),
        sa.column("web_blocklist"),
        sa.column("blocked_categories"),
        sa.column("set_by"),
        sa.column("created_at"),
    )
    for policy in bind.execute(sa.select(policies)).mappings():
        version = policy["version"] + 1
        bind.execute(
            sa.update(policies).where(policies.c.child_id == policy["child_id"]).values(version=version, updated_at=at)
        )
        bind.execute(
            sa.insert(history).values(
                child_id=policy["child_id"],
                version=version,
                weekday_quota_minutes=policy["weekday_quota_minutes"],
                weekend_quota_minutes=policy["weekend_quota_minutes"],
                weekly_schedule=policy["weekly_schedule"],
                app_rules=policy["app_rules"],
                web_allowlist=policy["web_allowlist"],
                web_blocklist=policy["web_blocklist"],
                blocked_categories=policy["blocked_categories"],
                set_by=policy["updated_by"],
                created_at=at,
            )
        )
        old_versions = (
            sa.select(history.c.id)
            .where(history.c.child_id == policy["child_id"])
            .order_by(history.c.version.desc())
            .offset(50)
        )
        bind.execute(sa.delete(history).where(history.c.id.in_(old_versions)))


def downgrade() -> None:
    op.drop_index("ix_web_categories_category", table_name="web_categories")
    op.drop_table("web_categories")
    for table in ("policies", "policy_versions"):
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_constraint(f"ck_{table}_web_allowlist", type_="check")
            batch.drop_constraint(f"ck_{table}_web_blocklist", type_="check")
            batch.drop_constraint(f"ck_{table}_blocked_categories", type_="check")
            batch.drop_column("web_allowlist")
            batch.drop_column("web_blocklist")
            batch.drop_column("blocked_categories")
