"""Idle time and locking use user32 through ctypes because both must run inside the user's session, which is
why the Tray UI and not the service calls them. GetTickCount wraps every 49.7 days, so the difference is taken
modulo 2^32.
foreground_app reads only the process image name, never the window title. UWP apps draw inside
ApplicationFrameHost.exe, so for that host the real app is the child window owned by another process.
"""

import ctypes
import ntpath
import os
import threading
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

import pystray


def data_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "OGK"


def run_tray(icon: pystray.Icon, root: tk.Tk) -> None:
    threading.Thread(target=icon.run, name="tray-icon", daemon=True).start()
    root.mainloop()


_tray_mutex = None


def acquire_single_instance() -> bool:
    """Allow only one tray process in this interactive Windows session."""
    global _tray_mutex
    ctypes.set_last_error(0)
    handle = _kernel32.CreateMutexW(None, False, "Local\\OGKTraySingleton")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        _kernel32.CloseHandle(handle)
        return False
    _tray_mutex = handle
    return True


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


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_PATH_CHARS = 32768
FRAME_HOST = "applicationframehost.exe"

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumChildWindows.argtypes = [wintypes.HWND, _ENUM_PROC, wintypes.LPARAM]
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def _window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _process_name(pid: int) -> str | None:
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(MAX_PATH_CHARS)
        size = wintypes.DWORD(MAX_PATH_CHARS)
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return ntpath.basename(buffer.value).lower() or None
    finally:
        _kernel32.CloseHandle(handle)


def _hosted_app(hwnd: int, host_pid: int) -> str | None:
    found: list[int] = []

    def visit(child: int, _param: int) -> bool:
        pid = _window_pid(child)
        if pid and pid != host_pid:
            found.append(pid)
            return False
        return True

    _user32.EnumChildWindows(hwnd, _ENUM_PROC(visit), 0)
    return _process_name(found[0]) if found else None


def foreground_app() -> str | None:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = _window_pid(hwnd)
    if not pid:
        return None
    name = _process_name(pid)
    if name == FRAME_HOST:
        return _hosted_app(hwnd, pid) or name
    return name
