"""family: children.id AUTOINCREMENT (không cấp lại id đã xóa)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _recreate_children(autoincrement: bool) -> None:
    # SQLite không ALTER được AUTOINCREMENT nên phải dựng lại bảng. Tắt khóa ngoại trong lúc dựng lại,
    # nếu không DROP bảng cũ sẽ kích hoạt ON DELETE SET NULL và bỏ gán mọi windows_accounts.
    # PRAGMA foreign_keys không có tác dụng trong giao dịch nên chạy ngoài giao dịch.
    with op.get_context().autocommit_block():
        op.execute('PRAGMA foreign_keys=OFF')
    with op.batch_alter_table(
        'children', recreate='always', table_kwargs={'sqlite_autoincrement': autoincrement}
    ):
        pass
    with op.get_context().autocommit_block():
        op.execute('PRAGMA foreign_keys=ON')
    violations = op.get_bind().exec_driver_sql('PRAGMA foreign_key_check').fetchall()
    if violations:
        raise RuntimeError(f'Vi phạm khóa ngoại sau khi dựng lại children: {violations}')


def upgrade() -> None:
    _recreate_children(True)
    # Trẻ đã xóa trước bản này có thể có id lớn hơn mọi id còn lại; id đó nằm trong nhật ký kiểm toán.
    # Đẩy bộ đếm lên trên mọi id từng thấy để không cấp lại.
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
