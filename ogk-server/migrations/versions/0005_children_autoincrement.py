"""family: children.id AUTOINCREMENT (never reuse deleted ids)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 11:00:00.000000

SQLite cannot ALTER a column to AUTOINCREMENT, so the table is rebuilt. Foreign keys are turned off during
the rebuild, otherwise dropping the old table fires ON DELETE SET NULL and unassigns every windows_account.
PRAGMA foreign_keys has no effect inside a transaction, so it runs in an autocommit block.
Children deleted before this revision may have ids above every remaining id; those ids live in audit_logs,
so the sequence is raised above every id ever seen.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _recreate_children(autoincrement: bool) -> None:
    with op.get_context().autocommit_block():
        op.execute("PRAGMA foreign_keys=OFF")
    with op.batch_alter_table("children", recreate="always", table_kwargs={"sqlite_autoincrement": autoincrement}):
        pass
    with op.get_context().autocommit_block():
        op.execute("PRAGMA foreign_keys=ON")
    violations = op.get_bind().exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"Foreign key violations after rebuilding children: {violations}")


def upgrade() -> None:
    _recreate_children(True)
    max_seen = (
        "MAX(COALESCE((SELECT MAX(id) FROM children), 0), "
        "COALESCE((SELECT MAX(target_id) FROM audit_logs WHERE target_type = 'child'), 0))"
    )
    op.execute(f"UPDATE sqlite_sequence SET seq = {max_seen} WHERE name = 'children'")
    op.execute(
        f"INSERT INTO sqlite_sequence (name, seq) SELECT 'children', {max_seen} "
        "WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = 'children')"
    )


def downgrade() -> None:
    _recreate_children(False)
