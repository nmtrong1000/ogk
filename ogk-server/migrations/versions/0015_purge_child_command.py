"""Command type purge_child, and AUTOINCREMENT on parent_commands and child_requests.

The agent remembers command ids it has run and request ids it shows, so an id reused after the retention
purge would make it skip a new command; AUTOINCREMENT never hands out an id again. Rebuilding the table
keeps its rows, so sqlite_sequence starts above the highest id still stored.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_TYPES = "'lock', 'unlock', 'add_time'"
NEW_TYPES = "'lock', 'unlock', 'add_time', 'purge_child'"


def _rebuild(autoincrement: bool, command_types: str) -> None:
    kwargs = {"sqlite_autoincrement": autoincrement}
    with op.batch_alter_table("parent_commands", recreate="always", table_kwargs=kwargs) as batch_op:
        batch_op.drop_constraint("ck_parent_commands_type", type_="check")
        batch_op.create_check_constraint("ck_parent_commands_type", f"type IN ({command_types})")
    with op.batch_alter_table("child_requests", recreate="always", table_kwargs=kwargs):
        pass


def upgrade() -> None:
    _rebuild(True, NEW_TYPES)


def downgrade() -> None:
    op.execute("DELETE FROM parent_commands WHERE type = 'purge_child'")
    _rebuild(False, OLD_TYPES)
