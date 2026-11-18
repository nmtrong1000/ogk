"""Tokens and the device secret are stored as DPAPI blobs; only device_id, timestamps, the server URL and
the certificate pin are plain. open() locks the data directory and the DB file to SYSTEM and Administrators
every time, because the installer or an older version may have left wider permissions.
The schema version lives in PRAGMA user_version; migrate() applies steps above the stored version.
Methods are synchronous; async callers run them in a worker thread.
"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from service.platform import dpapi, get_platform

DB_FILE = "agent.db"

SCHEMA = [
    """
    CREATE TABLE credentials (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        device_id INTEGER NOT NULL,
        server_url TEXT NOT NULL,
        cert_sha256 TEXT NOT NULL,
        device_secret BLOB NOT NULL,
        access_token BLOB NOT NULL,
        access_expires_at TEXT NOT NULL,
        refresh_token BLOB NOT NULL,
        enrolled_at TEXT NOT NULL,
        revoked_at TEXT
    )
    """,
]


@dataclass(frozen=True)
class Credentials:
    device_id: int
    server_url: str
    cert_sha256: str
    device_secret: str
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    enrolled_at: datetime
    revoked_at: datetime | None = None


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _parse(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _seal(value: str) -> bytes:
    return dpapi.protect(value.encode())


def _open(blob: bytes) -> str:
    return dpapi.unprotect(blob).decode()


class LocalDb:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.path = data_dir / DB_FILE

    def _connect(self) -> sqlite3.Connection:
        platform = get_platform()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        platform.secure_path(self.data_dir)
        conn = sqlite3.connect(self.path)
        platform.secure_path(self.path)
        self._migrate(conn)
        return conn

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for number, statement in enumerate(SCHEMA[version:], start=version + 1):
            with conn:
                conn.execute(statement)
                conn.execute(f"PRAGMA user_version = {number}")

    def schema_version(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("PRAGMA user_version").fetchone()[0]

    def load(self) -> Credentials | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT device_id, server_url, cert_sha256, device_secret, access_token, access_expires_at, "
                "refresh_token, enrolled_at, revoked_at FROM credentials WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return Credentials(
            device_id=row[0],
            server_url=row[1],
            cert_sha256=row[2],
            device_secret=_open(row[3]),
            access_token=_open(row[4]),
            access_expires_at=_parse(row[5]),
            refresh_token=_open(row[6]),
            enrolled_at=_parse(row[7]),
            revoked_at=_parse(row[8]),
        )

    def save(self, creds: Credentials) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO credentials (id, device_id, server_url, cert_sha256, device_secret, "
                "access_token, access_expires_at, refresh_token, enrolled_at, revoked_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    creds.device_id,
                    creds.server_url,
                    creds.cert_sha256,
                    _seal(creds.device_secret),
                    _seal(creds.access_token),
                    _iso(creds.access_expires_at),
                    _seal(creds.refresh_token),
                    _iso(creds.enrolled_at),
                    None if creds.revoked_at is None else _iso(creds.revoked_at),
                ),
            )

    def update_tokens(
        self, creds: Credentials, access_token: str, access_expires_at: datetime, refresh_token: str
    ) -> Credentials:
        updated = replace(
            creds, access_token=access_token, access_expires_at=access_expires_at, refresh_token=refresh_token
        )
        self.save(updated)
        return updated

    def mark_revoked(self, creds: Credentials, at: datetime) -> Credentials:
        updated = replace(creds, revoked_at=at)
        self.save(updated)
        return updated
