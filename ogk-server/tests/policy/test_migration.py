import sqlite3
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2]


def alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(SERVER_DIR / "alembic.ini"), *args],
        cwd=SERVER_DIR,
        check=True,
        capture_output=True,
    )


def test_upgrade_creates_policies_and_downgrade_drops_it(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    alembic("upgrade", "head")
    conn = sqlite3.connect(db)
    columns = {r[1] for r in conn.execute("PRAGMA table_info(policies)")}
    assert columns == {"child_id", "version", "daily_quota_minutes", "updated_at"}
    alembic("downgrade", "0006")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "policies" not in tables
