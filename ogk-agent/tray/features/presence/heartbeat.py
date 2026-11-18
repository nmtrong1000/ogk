import contextlib
import threading

from tray.ipc_client import IpcClient, IpcError

HEARTBEAT_SECONDS = 5.0


def heartbeat_loop(client: IpcClient, stop: threading.Event, interval: float = HEARTBEAT_SECONDS) -> None:
    while not stop.is_set():
        with contextlib.suppress(IpcError):
            client.heartbeat()
        stop.wait(interval)


def start_heartbeat(client: IpcClient, interval: float = HEARTBEAT_SECONDS) -> threading.Event:
    stop = threading.Event()
    threading.Thread(target=heartbeat_loop, args=(client, stop, interval), name="heartbeat", daemon=True).start()
    return stop
