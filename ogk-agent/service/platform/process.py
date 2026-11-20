"""psutil leaves exe empty when access is denied; the service runs as LocalSystem so that only happens for
protected system processes, which app control never kills anyway.
read_chunks opens with SeBackupPrivilege and FILE_FLAG_BACKUP_SEMANTICS so the file's DACL is not checked:
the child owns files it copies and could otherwise deny SYSTEM read access to dodge hash rules.
protected_dirs lists exact folders, not trees (see rules.is_protected); SystemApps\\* means its direct
subfolders, which only TrustedInstaller can write.
"""

import os
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import ntsecuritycon
import psutil
import pywintypes
import win32api
import win32con
import win32file
import win32security
import win32ts

from service.core.process_info import ProcInfo

ATTRS = ["pid", "name", "exe", "create_time"]
CREATE_TIME_TOLERANCE = 0.01
SHARE_ALL = win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE
BACKUP_FLAGS = win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_SEQUENTIAL_SCAN

_backup_lock = threading.Lock()
_backup_enabled = False


def _session_id(pid: int) -> int | None:
    try:
        return win32ts.ProcessIdToSessionId(pid)
    except pywintypes.error:
        return None


def list_processes() -> list[ProcInfo]:
    processes = []
    for process in psutil.process_iter(ATTRS):
        info = process.info
        if info.get("create_time") is None:
            continue
        processes.append(
            ProcInfo(
                info["pid"],
                float(info["create_time"]),
                (info.get("name") or "").lower(),
                info.get("exe") or "",
                _session_id(info["pid"]),
            )
        )
    return processes


def terminate(pid: int, create_time: float) -> bool:
    try:
        process = psutil.Process(pid)
        if abs(process.create_time() - create_time) > CREATE_TIME_TOLERANCE:
            return False
        process.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    return True


def protected_dirs() -> list[str]:
    root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    dirs = [root, rf"{root}\System32", rf"{root}\SysWOW64", rf"{root}\SystemApps\*"]
    if getattr(sys, "frozen", False):
        dirs.append(str(Path(sys.executable).resolve().parent))
    return dirs


def _enable_backup_privilege() -> None:
    global _backup_enabled
    with _backup_lock:
        if _backup_enabled:
            return
        flags = ntsecuritycon.TOKEN_ADJUST_PRIVILEGES | ntsecuritycon.TOKEN_QUERY
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), flags)
        luid = win32security.LookupPrivilegeValue(None, ntsecuritycon.SE_BACKUP_NAME)
        win32security.AdjustTokenPrivileges(token, False, [(luid, ntsecuritycon.SE_PRIVILEGE_ENABLED)])
        _backup_enabled = True


def read_chunks(path: str, size: int) -> Iterator[bytes]:
    try:
        _enable_backup_privilege()
        handle = win32file.CreateFile(
            path, win32con.GENERIC_READ, SHARE_ALL, None, win32con.OPEN_EXISTING, BACKUP_FLAGS, None
        )
    except pywintypes.error as exc:
        raise OSError(exc.winerror, exc.strerror, path) from None
    try:
        while True:
            try:
                _, data = win32file.ReadFile(handle, size)
            except pywintypes.error as exc:
                raise OSError(exc.winerror, exc.strerror, path) from None
            if not data:
                return
            yield data
    finally:
        handle.Close()
