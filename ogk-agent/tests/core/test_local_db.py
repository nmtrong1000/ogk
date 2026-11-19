import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta

from service.core.local_db import DB_FILE, SCHEMA, Credentials, LocalDb, PolicyRow, SyncState


def creds(**overrides) -> Credentials:
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    values = {
        "device_id": 7,
        "server_url": "https://server",
        "cert_sha256": "a" * 64,
        "device_secret": "device-secret-value",
        "access_token": "access-token-value",
        "access_expires_at": now + timedelta(minutes=15),
        "refresh_token": "refresh-token-value",
        "enrolled_at": now,
    }
    values.update(overrides)
    return Credentials(**values)


def test_empty_db_has_no_credentials(data_dir):
    assert LocalDb(data_dir).load() is None


def test_save_and_load(data_dir):
    db = LocalDb(data_dir)
    db.save(creds())
    assert db.load() == creds()


def test_secrets_are_not_stored_in_plain_text(data_dir):
    LocalDb(data_dir).save(creds())
    raw = (data_dir / DB_FILE).read_bytes()
    for secret in (b"device-secret-value", b"access-token-value", b"refresh-token-value"):
        assert secret not in raw


def test_update_tokens_and_revoke(data_dir):
    db = LocalDb(data_dir)
    db.save(creds())
    expires = datetime(2026, 11, 18, 11, 0, tzinfo=UTC)
    updated = db.update_tokens(db.load(), "new-access", expires, "new-refresh")
    assert db.load() == updated
    assert (updated.access_token, updated.refresh_token, updated.access_expires_at) == (
        "new-access",
        "new-refresh",
        expires,
    )
    revoked = db.mark_revoked(updated, expires)
    assert db.load().revoked_at == expires == revoked.revoked_at


def test_dir_and_db_are_owner_only(data_dir):
    data_dir.chmod(0o755)
    LocalDb(data_dir).save(creds())
    assert data_dir.stat().st_mode & 0o777 == 0o700
    assert (data_dir / DB_FILE).stat().st_mode & 0o777 == 0o600


def test_schema_version(data_dir):
    assert LocalDb(data_dir).schema_version() == len(SCHEMA)


def test_replace_policies_swaps_the_whole_set(data_dir):
    at = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    db = LocalDb(data_dir)
    db.replace_policies([PolicyRow(7, 1, "{}", "s1"), PolicyRow(8, 1, "{}", "s2")], at)
    db.replace_policies([PolicyRow(8, 2, "{}", "s3")], at)
    assert db.load_policies() == [PolicyRow(8, 2, "{}", "s3")]


def test_upgrade_from_version_1_keeps_credentials(data_dir):
    with closing(sqlite3.connect(data_dir / DB_FILE)) as conn, conn:
        conn.execute(SCHEMA[0])
        conn.execute("PRAGMA user_version = 1")
    db = LocalDb(data_dir)
    db.save(creds())
    assert db.schema_version() == len(SCHEMA)
    assert db.load() == creds()
    assert db.load_policies() == []


def test_event_batch_keeps_key_until_deleted(data_dir):
    at = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    db = LocalDb(data_dir)
    db.add_events(["a", "b", "c"], at)
    keys = iter(["k1", "k2"])
    first = db.next_event_batch(2, lambda: next(keys))
    assert (first.key, first.payloads) == ("k1", ["a", "b"])
    db.add_events(["d"], at)
    assert db.next_event_batch(2, lambda: next(keys)) == first
    db.delete_event_batch("k1")
    second = db.next_event_batch(2, lambda: next(keys))
    assert (second.key, second.payloads) == ("k2", ["c", "d"])
    db.delete_event_batch("k2")
    assert db.next_event_batch(2, lambda: "unused") is None
    assert db.pending_events() == 0


def test_sync_state_round_trip(data_dir):
    db = LocalDb(data_dir)
    assert db.load_sync_state() == SyncState()
    state = SyncState(12.5, datetime(2026, 11, 18, 10, 0, tzinfo=UTC), datetime(2026, 11, 18, 10, 1, tzinfo=UTC))
    db.save_sync_state(state)
    assert db.load_sync_state() == state
