from datetime import UTC, datetime, timedelta

from service.core.local_db import DB_FILE, SCHEMA, Credentials, LocalDb


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
