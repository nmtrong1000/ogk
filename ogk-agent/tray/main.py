import queue
import tkinter as tk
from collections.abc import Callable

from tray.features.presence import StatusWindow, create_icon
from tray.ipc_client import IpcClient
from tray.platform import get_platform

POLL_MS = 100


def main() -> None:
    platform = get_platform()
    jobs: queue.Queue[Callable[[], None]] = queue.Queue()
    root = tk.Tk()
    root.withdraw()

    window = StatusWindow(root, IpcClient(platform.data_dir()), jobs.put)

    def quit_app() -> None:
        icon.stop()
        root.destroy()

    icon = create_icon(on_open=lambda: jobs.put(window.show), on_quit=lambda: jobs.put(quit_app))

    def drain() -> None:
        while True:
            try:
                job = jobs.get_nowait()
            except queue.Empty:
                break
            job()
            if job is quit_app:
                return
        root.after(POLL_MS, drain)

    root.after(POLL_MS, drain)
    platform.run_tray(icon, root)
