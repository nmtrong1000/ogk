import sqlite3

from tests.policy.test_migration import alembic


def test_upgrade_creates_sync_tables_and_downgrade_drops_them(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    alembic("upgrade", "head")
    conn = sqlite3.connect(db)
    columns = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    assert columns == {"id", "ts", "device_id", "child_id", "type", "subject", "duration_sec", "policy_id"}
    indexes = {r[1]: r[2] for r in conn.execute("PRAGMA index_list(device_alerts)")}
    assert indexes["uq_device_alerts_open"] == 1
    alembic("downgrade", "0007")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not tables & {"events", "event_batches", "device_alerts"}
