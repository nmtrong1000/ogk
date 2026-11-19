"""Tokens and the device secret are stored as DPAPI blobs; only device_id, timestamps, the server URL and
the certificate pin are plain. open() locks the data directory and the DB file to SYSTEM and Administrators
every time, because the installer or an older version may have left wider permissions.
The schema version lives in PRAGMA user_version; migrate() applies steps above the stored version.
policies rows are not trusted on read: policy_store re-verifies each signature, so this layer stores raw text.
next_event_batch assigns a batch_key and stores it before the batch is sent, so a resend after a lost response
carries the same key and the server ignores it; rows keep their key until the server acknowledges the batch.
usage keeps one row per child, local day and counter; old days stay until P17 reports on them.
Methods are synchronous; async callers run them in a worker thread.
"""

import sqlite3
from collections.abc import Callable
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
    """
    CREATE TABLE policies (
        child_id INTEGER PRIMARY KEY,
        version INTEGER NOT NULL,
        payload TEXT NOT NULL,
        signature TEXT NOT NULL,
        received_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE event_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload TEXT NOT NULL,
        batch_key TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE sync_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        offline_seconds REAL NOT NULL CHECK (offline_seconds >= 0),
        last_server_time TEXT,
        last_success_at TEXT
    )
    """,
    """
    CREATE TABLE usage (
        child_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        counter TEXT NOT NULL,
        seconds REAL NOT NULL CHECK (seconds >= 0),
        updated_at TEXT NOT NULL,
        PRIMARY KEY (child_id, day, counter)
    )
    """,
    """
    CREATE TABLE clock_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        last_trusted TEXT NOT NULL
    )
    """,
]


@dataclass(frozen=True)
class PolicyRow:
    child_id: int
    version: int
    payload: str
    signature: str


@dataclass(frozen=True)
class OutboxBatch:
    key: str
    ids: list[int]
    payloads: list[str]


@dataclass(frozen=True)
class SyncState:
    offline_seconds: float = 0.0
    last_server_time: datetime | None = None
    last_success_at: datetime | None = None


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

    def load_policies(self) -> list[PolicyRow]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT child_id, version, payload, signature FROM policies ORDER BY child_id")
            return [PolicyRow(*row) for row in rows]

    def replace_policies(self, rows: list[PolicyRow], received_at: datetime) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM policies")
            conn.executemany(
                "INSERT INTO policies (child_id, version, payload, signature, received_at) VALUES (?, ?, ?, ?, ?)",
                [(r.child_id, r.version, r.payload, r.signature, _iso(received_at)) for r in rows],
            )

    def add_events(self, payloads: list[str], created_at: datetime) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                "INSERT INTO event_outbox (payload, created_at) VALUES (?, ?)",
                [(payload, _iso(created_at)) for payload in payloads],
            )

    def next_event_batch(self, limit: int, new_key: Callable[[], str]) -> OutboxBatch | None:
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                "SELECT batch_key FROM event_outbox WHERE batch_key IS NOT NULL ORDER BY id LIMIT 1"
            ).fetchone()
            if row is not None:
                key = row[0]
            else:
                ids = [r[0] for r in conn.execute("SELECT id FROM event_outbox ORDER BY id LIMIT ?", (limit,))]
                if not ids:
                    return None
                key = new_key()
                conn.executemany("UPDATE event_outbox SET batch_key = ? WHERE id = ?", [(key, i) for i in ids])
            rows = conn.execute(
                "SELECT id, payload FROM event_outbox WHERE batch_key = ? ORDER BY id", (key,)
            ).fetchall()
        return OutboxBatch(key, [r[0] for r in rows], [r[1] for r in rows])

    def delete_event_batch(self, key: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM event_outbox WHERE batch_key = ?", (key,))

    def pending_events(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM event_outbox").fetchone()[0]

    def load_sync_state(self) -> SyncState:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT offline_seconds, last_server_time, last_success_at FROM sync_state WHERE id = 1"
            ).fetchone()
        if row is None:
            return SyncState()
        return SyncState(row[0], _parse(row[1]), _parse(row[2]))

    def save_sync_state(self, state: SyncState) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO sync_state (id, offline_seconds, last_server_time, last_success_at) "
                "VALUES (1, ?, ?, ?)",
                (
                    state.offline_seconds,
                    None if state.last_server_time is None else _iso(state.last_server_time),
                    None if state.last_success_at is None else _iso(state.last_success_at),
                ),
            )

    def load_usage(self, day: str) -> dict[tuple[int, str], float]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT child_id, counter, seconds FROM usage WHERE day = ?", (day,)).fetchall()
        return {(child_id, counter): seconds for child_id, counter, seconds in rows}

    def save_usage(self, day: str, values: dict[tuple[int, str], float], updated_at: datetime) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                "INSERT INTO usage (child_id, day, counter, seconds, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (child_id, day, counter) DO UPDATE SET seconds = excluded.seconds, "
                "updated_at = excluded.updated_at",
                [
                    (child_id, day, counter, seconds, _iso(updated_at))
                    for (child_id, counter), seconds in values.items()
                ],
            )

    def load_last_trusted(self) -> datetime | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT last_trusted FROM clock_state WHERE id = 1").fetchone()
        return None if row is None else _parse(row[0])

    def save_last_trusted(self, at: datetime) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO clock_state (id, last_trusted) VALUES (1, ?)", (_iso(at),))
