import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SCHEDULE = ("0" * 14 + "1" * 28 + "0" * 6) * 7


def alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(SERVER_DIR / "alembic.ini"), *args],
        cwd=SERVER_DIR,
        check=True,
        capture_output=True,
    )


def seed_0008(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO accounts (id, email, password_hash, role, failed_attempts, created_at) "
        "VALUES (5, 'p@example.com', 'x', 'parent', 0, '2026-11-18 08:00:00')"
    )
    conn.execute(
        "INSERT INTO children (id, owner_id, name, birth_year, created_at, updated_at) "
        "VALUES (7, 5, 'x', 2015, '2026-11-18 08:00:00', '2026-11-18 08:00:00')"
    )
    conn.execute("INSERT INTO policies VALUES (7, 3, 45, '2026-11-18 08:00:00')")
    conn.commit()


def table_sql(conn: sqlite3.Connection, name: str) -> str:
    return conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]


@pytest.fixture
def db(settings_env, tmp_path, monkeypatch):
    path = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    return path


def test_upgrade_splits_quota_and_backfills_history(db):
    alembic("upgrade", "0008")
    conn = sqlite3.connect(db)
    seed_0008(conn)
    alembic("upgrade", "head")
    columns = {r[1] for r in conn.execute("PRAGMA table_info(policies)")}
    assert columns == {
        "child_id",
        "version",
        "weekday_quota_minutes",
        "weekend_quota_minutes",
        "weekly_schedule",
        "updated_by",
        "updated_at",
    }
    assert conn.execute(
        "SELECT version, weekday_quota_minutes, weekend_quota_minutes, weekly_schedule, updated_by FROM policies"
    ).fetchone() == (3, 45, 45, DEFAULT_SCHEDULE, 5)
    assert conn.execute("SELECT child_id, version, weekday_quota_minutes, set_by FROM policy_versions").fetchall() == [
        (7, 3, 45, 5)
    ]
    sql = table_sql(conn, "policies")
    for name in ("ck_policies_version", "ck_policies_weekday_quota_minutes", "ck_policies_weekly_schedule"):
        assert name in sql
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE policies SET weekly_schedule = '1'")


def test_downgrade_restores_daily_quota(db):
    alembic("upgrade", "0008")
    conn = sqlite3.connect(db)
    seed_0008(conn)
    alembic("upgrade", "head")
    alembic("downgrade", "0008")
    assert conn.execute("SELECT child_id, version, daily_quota_minutes FROM policies").fetchone() == (7, 3, 45)
    assert {r[1] for r in conn.execute("PRAGMA table_info(policies)")} == {
        "child_id",
        "version",
        "daily_quota_minutes",
        "updated_at",
    }
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "policy_versions" not in tables
    assert "ck_policies_daily_quota_minutes" in table_sql(conn, "policies")
    alembic("downgrade", "0006")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "policies" not in tables
