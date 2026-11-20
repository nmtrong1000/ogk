"""The idle time and the foreground app ride on the presence heartbeat so the service gets them without a
second loop; a failing reader sends no value, and the service then counts screen time but no app time.
The foreground app is checked every second and a change is sent at once, so app time is not off by a whole
heartbeat interval; otherwise a heartbeat goes out every interval seconds.
"""

import contextlib
import logging
import threading
import time
from collections.abc import Callable

from tray.ipc_client import IpcClient, IpcError

HEARTBEAT_SECONDS = 5.0
FOREGROUND_SECONDS = 1.0

log = logging.getLogger("ogk.tray")

IdleReader = Callable[[], float]
ForegroundReader = Callable[[], str | None]


def _idle(reader: IdleReader | None) -> float | None:
    if reader is None:
        return None
    try:
        return reader()
    except OSError as exc:
        log.warning("cannot read idle time: %s", exc)
        return None


def _foreground(reader: ForegroundReader | None) -> str | None:
    if reader is None:
        return None
    try:
        return reader()
    except OSError as exc:
        log.warning("cannot read foreground app: %s", exc)
        return None


def heartbeat_loop(
    client: IpcClient,
    stop: threading.Event,
    interval: float = HEARTBEAT_SECONDS,
    idle: IdleReader | None = None,
    foreground: ForegroundReader | None = None,
    check: float = FOREGROUND_SECONDS,
) -> None:
    sent_at: float | None = None
    last_app: str | None = None
    while not stop.is_set():
        app = _foreground(foreground)
        now = time.monotonic()
        if sent_at is None or now - sent_at >= interval or app != last_app:
            with contextlib.suppress(IpcError):
                client.heartbeat(_idle(idle), app)
            sent_at, last_app = now, app
        stop.wait(min(interval, check))


def start_heartbeat(
    client: IpcClient,
    interval: float = HEARTBEAT_SECONDS,
    idle: IdleReader | None = None,
    foreground: ForegroundReader | None = None,
) -> threading.Event:
    stop = threading.Event()
    threading.Thread(
        target=heartbeat_loop, args=(client, stop, interval, idle, foreground), name="heartbeat", daemon=True
    ).start()
    return stop
