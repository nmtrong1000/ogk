import sqlite3

from tests.policy.test_migration import alembic


def table_sql(conn: sqlite3.Connection, table: str) -> str:
    return conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0]


def type_check(conn: sqlite3.Connection) -> str:
    return next(line for line in table_sql(conn, "parent_commands").splitlines() if "ck_parent_commands_type" in line)


def index_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA index_list({table})")}


def test_upgrade_allows_purge_child_and_never_reuses_ids(settings_env, tmp_path, monkeypatch):
    db = tmp_path / "migrate.db"
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    alembic("upgrade", "0014")
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO accounts (id, email, password_hash, role, failed_attempts, created_at) "
        "VALUES (5, 'p@example.com', 'x', 'parent', 0, '2026-11-18 08:00:00')"
    )
    conn.execute(
        "INSERT INTO children (id, owner_id, name, birth_year, created_at, updated_at) "
        "VALUES (7, 5, 'x', 'x', '2026-11-18 08:00:00', '2026-11-18 08:00:00')"
    )
    conn.execute(
        "INSERT INTO devices (id, owner_id, name, created_at, fingerprint_hash, secret_hash) "
        "VALUES (3, 5, 'PC', '2026-11-18 08:00:00', 'f', 's')"
    )
    conn.execute(
        "INSERT INTO parent_commands (id, device_id, child_id, actor_id, type, created_at) "
        "VALUES (17, 3, 7, 5, 'lock', '2026-11-18 08:00:00')"
    )
    conn.execute(
        "INSERT INTO child_requests (id, device_id, child_id, type, created_at) "
        "VALUES (9, 3, 7, 'add_time', '2026-11-18 08:00:00')"
    )
    conn.commit()
    indexes = {t: index_names(conn, t) for t in ("parent_commands", "child_requests")}

    alembic("upgrade", "head")

    assert "'purge_child'" in type_check(conn)
    assert {t: index_names(conn, t) for t in indexes} == indexes
    conn.execute("DELETE FROM parent_commands")
    conn.execute("DELETE FROM child_requests")
    conn.execute(
        "INSERT INTO parent_commands (device_id, child_id, actor_id, type, created_at) "
        "VALUES (3, 7, 5, 'purge_child', '2026-11-24 08:00:00')"
    )
    conn.execute(
        "INSERT INTO child_requests (device_id, child_id, type, created_at) VALUES (3, 7, 'add_time', '2026-11-24')"
    )
    conn.commit()
    assert conn.execute("SELECT id FROM parent_commands").fetchone()[0] == 18
    assert conn.execute("SELECT id FROM child_requests").fetchone()[0] == 10

    alembic("downgrade", "0014")
    assert "'purge_child'" not in type_check(conn)
    assert "AUTOINCREMENT" not in table_sql(conn, "parent_commands")
    assert conn.execute("SELECT count(*) FROM parent_commands").fetchone()[0] == 0
