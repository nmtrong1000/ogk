import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import csrf_headers
from tests.family.conftest import create_child

SERVER_DIR = Path(__file__).resolve().parents[2]


@pytest.mark.anyio
async def test_deleted_child_id_not_reused(parent):
    first = (await create_child(parent, "An")).json()
    assert (await parent.delete(f"/api/children/{first['id']}", headers=await csrf_headers(parent))).status_code == 204
    second = (await create_child(parent, "Bình")).json()
    assert second["id"] > first["id"]


def _alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(SERVER_DIR / "alembic.ini"), *args],
        cwd=SERVER_DIR,
        check=True,
        capture_output=True,
    )


def test_migration_0005_keeps_data_and_assignments(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    _alembic("upgrade", "0004")
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        INSERT INTO accounts (id, email, password_hash, role, failed_attempts, created_at)
            VALUES (1, 'p@example.com', 'x', 'parent', 0, '2026-01-01');
        INSERT INTO children (id, owner_id, name, birth_year, created_at, updated_at)
            VALUES (1, 1, x'01', x'01', '2026-01-01', '2026-01-01'), (2, 1, x'02', x'02', '2026-01-01', '2026-01-01');
        INSERT INTO devices (id, owner_id, name, created_at) VALUES (1, 1, 'PC', '2026-01-01');
        INSERT INTO windows_accounts (id, device_id, child_id, sid, username) VALUES (1, 1, 2, 'S-1', x'03');
        INSERT INTO audit_logs (actor_id, at, ip, action, target_type, target_id)
            VALUES (1, '2026-01-01', '::1', 'delete', 'child', 5);
        """
    )
    conn.commit()
    conn.close()

    _alembic("upgrade", "head")

    conn = sqlite3.connect(db)
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'children'").fetchone()[0]
    assert "AUTOINCREMENT" in sql
    assert [r[0] for r in conn.execute("SELECT id FROM children ORDER BY id")] == [1, 2]
    assert conn.execute("SELECT child_id FROM windows_accounts WHERE id = 1").fetchone()[0] == 2
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.execute(
        "INSERT INTO children (owner_id, name, birth_year, created_at, updated_at) "
        "VALUES (1, x'04', x'04', '2026-01-01', '2026-01-01')"
    )
    assert conn.execute("SELECT MAX(id) FROM children").fetchone()[0] == 6
    conn.close()

    _alembic("downgrade", "0004")
    conn = sqlite3.connect(db)
    assert "AUTOINCREMENT" not in conn.execute("SELECT sql FROM sqlite_master WHERE name = 'children'").fetchone()[0]
    assert conn.execute("SELECT child_id FROM windows_accounts WHERE id = 1").fetchone()[0] == 2
