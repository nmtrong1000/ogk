import os
import threading
import tkinter as tk
from pathlib import Path

import pystray


def data_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "OGK"


def run_tray(icon: pystray.Icon, root: tk.Tk) -> None:
    threading.Thread(target=icon.run, name="tray-icon", daemon=True).start()
    root.mainloop()


def notify(icon: pystray.Icon, title: str, message: str) -> None:
    icon.notify(message, title)
