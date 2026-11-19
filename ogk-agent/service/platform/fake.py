"""Mac stand-ins for Windows-only calls. OGK_FAKE_ADMIN=0 simulates a non-admin shell; OGK_FAKE_ACCOUNTS
("user:SID,user:SID") replaces the two default accounts. ACLs map to POSIX modes: owner-only for the data
dir and DB, world-readable for files the Tray UI must read.
Session changes: run `python ogk_service.py fake-session logon|logoff|lock|unlock` while the service runs;
the command appends to fake_session.jsonl and the service polls that file, reading only lines added after
it started. OGK_FAKE_TRAY_CMD replaces the Tray UI command line, e.g. /usr/bin/false to simulate a Tray UI
that cannot start. OGK_FAKE_SESSION_USER picks which fake account is logged on (default: the first one), so its
SID is what screen time matches against the signed policies.
"""

import asyncio
import getpass
import hashlib
import json
import logging
import os
import shlex
import signal
import subprocess
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

from service.core.bus import SESSION_KINDS, SessionEvent, SessionInfo
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


AGENT_ROOT = Path(__file__).resolve().parents[2]
SESSION_FILE = "fake_session.jsonl"
FAKE_SESSION_ID = 1
SESSION_POLL_SECONDS = 1.0

_listener: Callable[[SessionEvent], None] | None = None
_logged_on = True


def set_session_listener(listener: Callable[[SessionEvent], None] | None) -> None:
    global _listener
    _listener = listener


def current_session() -> SessionInfo | None:
    if not _logged_on:
        return None
    accounts = dict(list_windows_accounts())
    username = os.environ.get("OGK_FAKE_SESSION_USER") or next(iter(accounts), getpass.getuser())
    return SessionInfo(FAKE_SESSION_ID, username, accounts.get(username, ""))


def session_command(argv: list[str], directory: Path) -> int:
    if len(argv) != 1 or argv[0] not in SESSION_KINDS:
        print(f"usage: ogk_service fake-session {'|'.join(SESSION_KINDS)}", file=sys.stderr)
        return 2
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / SESSION_FILE).open("a", encoding="utf-8") as file:
        file.write(json.dumps({"event": argv[0], "session_id": FAKE_SESSION_ID}) + "\n")
    print(f"session event {argv[0]} sent")
    return 0


def read_session_events(path: Path, offset: int) -> tuple[list[SessionEvent], int]:
    try:
        with path.open("rb") as file:
            file.seek(offset)
            data = file.read()
    except FileNotFoundError:
        return [], 0
    end = data.rfind(b"\n") + 1
    events = []
    for line in data[:end].splitlines():
        try:
            raw = json.loads(line)
            kind, session_id = raw["event"], int(raw["session_id"])
        except (ValueError, KeyError, TypeError):
            log.warning("ignoring bad line in %s", path.name)
            continue
        if kind in SESSION_KINDS:
            events.append(SessionEvent(kind, session_id))
    return events, offset + end


def dispatch_session_event(event: SessionEvent) -> None:
    global _logged_on
    if event.kind == "logon":
        _logged_on = True
    elif event.kind == "logoff":
        _logged_on = False
    if _listener is not None:
        _listener(event)


async def watch_session_file(path: Path, interval: float = SESSION_POLL_SECONDS) -> None:
    offset = path.stat().st_size if path.exists() else 0
    while True:
        await asyncio.sleep(interval)
        events, offset = read_session_events(path, offset)
        for event in events:
            dispatch_session_event(event)


class TrayProcess:
    def __init__(self, process: subprocess.Popen) -> None:
        self._process = process

    @property
    def pid(self) -> int:
        return self._process.pid

    def alive(self) -> bool:
        return self._process.poll() is None

    def terminate(self) -> None:
        if not self.alive():
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()


def tray_command() -> list[str]:
    override = os.environ.get("OGK_FAKE_TRAY_CMD")
    if override:
        return shlex.split(override)
    return [sys.executable, str(AGENT_ROOT / "ogk_tray.py")]


def launch_tray(session_id: int) -> TrayProcess:
    env = {**os.environ, "OGK_DATA_DIR": str(data_dir())}
    process = subprocess.Popen(tray_command(), cwd=AGENT_ROOT, env=env, stdin=subprocess.DEVNULL)
    return TrayProcess(process)


def run_service(argv: list[str], entry: Entry) -> None:
    directory = data_dir()
    setup_logging(directory, console=True)
    log.info("fake platform, data dir %s", directory)

    async def _main() -> None:
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        watcher = asyncio.create_task(watch_session_file(directory / SESSION_FILE))
        try:
            await entry(directory, stop_event)
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)

    asyncio.run(_main())
