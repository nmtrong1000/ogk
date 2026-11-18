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


def test_upgrade_creates_enrollment_tables(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    alembic("upgrade", "head")
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"pairing_codes", "device_tokens", "consent_records"} <= tables
    columns = {r[1] for r in conn.execute("PRAGMA table_info(devices)")}
    assert {"fingerprint_hash", "secret_hash", "revoked_at", "last_seen_at"} <= columns


def test_upgrade_keeps_existing_windows_accounts(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    alembic("upgrade", "0005")
    conn = sqlite3.connect(db)
    conn.executescript(
        "INSERT INTO accounts (email, password_hash, role, failed_attempts, created_at) "
        "VALUES ('a@b.c', 'x', 'parent', 0, '2026-01-01');"
        "INSERT INTO devices (owner_id, name, created_at) VALUES (1, 'pc', '2026-01-01');"
        "INSERT INTO windows_accounts (device_id, sid, username) VALUES (1, 'S-1', x'00');"
    )
    conn.commit()
    conn.close()
    alembic("upgrade", "head")
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT count(*) FROM windows_accounts").fetchone() == (1,)
    alembic("downgrade", "0005")
    assert conn.execute("SELECT count(*) FROM windows_accounts").fetchone() == (1,)
