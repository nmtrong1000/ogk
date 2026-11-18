"""Mac stand-ins for Windows-only calls. OGK_FAKE_ADMIN=0 simulates a non-admin shell; OGK_FAKE_ACCOUNTS
("user:SID,user:SID") replaces the two default accounts. ACLs map to POSIX modes: owner-only for the data
dir and DB, world-readable for files the Tray UI must read.
"""

import asyncio
import hashlib
import logging
import os
import signal
import uuid
from pathlib import Path

from service.core.logging_setup import setup_logging
from service.platform import Entry

log = logging.getLogger("ogk.platform")


def data_dir() -> Path:
    return Path(os.environ.get("OGK_DATA_DIR", ".ogk-data")).resolve()


FAKE_MACHINE_ID = "fake-machine-id"
DEFAULT_ACCOUNTS = [("an", "S-1-5-21-1000-1000-1000-1001"), ("binh", "S-1-5-21-1000-1000-1000-1002")]


def is_admin() -> bool:
    return os.environ.get("OGK_FAKE_ADMIN", "1") != "0"


def machine_fingerprint() -> str:
    path = data_dir() / FAKE_MACHINE_ID
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(uuid.uuid4()), encoding="utf-8")
    return hashlib.sha256(path.read_text(encoding="utf-8").strip().encode()).hexdigest()


def list_windows_accounts() -> list[tuple[str, str]]:
    raw = os.environ.get("OGK_FAKE_ACCOUNTS")
    if not raw:
        return list(DEFAULT_ACCOUNTS)
    accounts = []
    for item in raw.split(","):
        username, _, sid = item.strip().partition(":")
        if username and sid:
            accounts.append((username, sid))
    return accounts


def secure_path(path: Path, user_readable: bool = False) -> None:
    if user_readable:
        os.chmod(path, 0o644)
    else:
        os.chmod(path, 0o700 if path.is_dir() else 0o600)


def run_service(argv: list[str], entry: Entry) -> None:
    directory = data_dir()
    setup_logging(directory, console=True)
    log.info("fake platform, data dir %s", directory)

    async def _main() -> None:
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await entry(directory, stop_event)

    asyncio.run(_main())
