"""The idle time rides on the presence heartbeat so the service gets it every 5 seconds without a second
loop; a failing idle reader sends no value and the service then counts the time.
"""

import contextlib
import logging
import threading
from collections.abc import Callable

from tray.ipc_client import IpcClient, IpcError

HEARTBEAT_SECONDS = 5.0

log = logging.getLogger("ogk.tray")

IdleReader = Callable[[], float]


def _idle(reader: IdleReader | None) -> float | None:
    if reader is None:
        return None
    try:
        return reader()
    except OSError as exc:
        log.warning("cannot read idle time: %s", exc)
        return None


def heartbeat_loop(
    client: IpcClient, stop: threading.Event, interval: float = HEARTBEAT_SECONDS, idle: IdleReader | None = None
) -> None:
    while not stop.is_set():
        with contextlib.suppress(IpcError):
            client.heartbeat(_idle(idle))
        stop.wait(interval)


def start_heartbeat(
    client: IpcClient, interval: float = HEARTBEAT_SECONDS, idle: IdleReader | None = None
) -> threading.Event:
    stop = threading.Event()
    threading.Thread(target=heartbeat_loop, args=(client, stop, interval, idle), name="heartbeat", daemon=True).start()
    return stop
