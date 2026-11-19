"""Idle time and locking use user32 through ctypes because both must run inside the user's session, which is
why the Tray UI and not the service calls them. GetTickCount wraps every 49.7 days, so the difference is taken
modulo 2^32.
"""

import ctypes
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


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds() -> float:
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    ticks = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    return ((ticks - info.dwTime) & 0xFFFFFFFF) / 1000.0


def lock_workstation() -> bool:
    return bool(ctypes.windll.user32.LockWorkStation())
