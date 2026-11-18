import sqlite3
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2]


def test_alembic_upgrade_creates_audit_table_and_triggers(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(SERVER_DIR / "alembic.ini"), "upgrade", "head"],
        cwd=SERVER_DIR,
        check=True,
        capture_output=True,
    )
    conn = sqlite3.connect(db)
    names = {(r[0], r[1]) for r in conn.execute("SELECT type, name FROM sqlite_master")}
    assert ("table", "audit_logs") in names
    assert {("trigger", "audit_logs_no_update"), ("trigger", "audit_logs_no_delete")} <= names
