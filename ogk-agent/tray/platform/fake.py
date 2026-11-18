"""Fake tray platform for macOS. pystray and Tk both need the main thread, so pystray shares the Tk run loop.
Notifications go through osascript because pystray's macOS backend does not show them for an unbundled
Python process.
"""

import contextlib
import json
import os
import subprocess
import tkinter as tk
from pathlib import Path

import pystray


def data_dir() -> Path:
    return Path(os.environ.get("OGK_DATA_DIR", ".ogk-data")).resolve()


def run_tray(icon: pystray.Icon, root: tk.Tk) -> None:
    icon.run_detached()
    root.mainloop()


def _quote(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def notify(icon: pystray.Icon, title: str, message: str) -> None:
    script = f"display notification {_quote(message)} with title {_quote(title)}"
    with contextlib.suppress(OSError):
        subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
