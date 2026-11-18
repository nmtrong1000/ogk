import queue
import tkinter as tk
from collections.abc import Callable

from tray.features.presence import STARTUP_MESSAGE, STARTUP_TITLE, StatusWindow, create_icon, start_heartbeat
from tray.ipc_client import IpcClient
from tray.platform import get_platform

POLL_MS = 100
NOTIFY_DELAY_MS = 1500


def main() -> None:
    platform = get_platform()
    jobs: queue.Queue[Callable[[], None]] = queue.Queue()
    root = tk.Tk()
    root.withdraw()

    client = IpcClient(platform.data_dir())
    window = StatusWindow(root, client, jobs.put)
    icon = create_icon(on_open=lambda: jobs.put(window.show))

    def drain() -> None:
        while True:
            try:
                job = jobs.get_nowait()
            except queue.Empty:
                break
            job()
        root.after(POLL_MS, drain)

    root.after(POLL_MS, drain)
    root.after(NOTIFY_DELAY_MS, lambda: platform.notify(icon, STARTUP_TITLE, STARTUP_MESSAGE))
    start_heartbeat(client)
    platform.run_tray(icon, root)
