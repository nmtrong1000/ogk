"""Fake tray platform for macOS. pystray and Tk both need the main thread, so pystray shares the Tk run loop."""

import os
import tkinter as tk
from pathlib import Path

import pystray


def data_dir() -> Path:
    return Path(os.environ.get("OGK_DATA_DIR", ".ogk-data")).resolve()


def run_tray(icon: pystray.Icon, root: tk.Tk) -> None:
    icon.run_detached()
    root.mainloop()
