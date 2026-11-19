"""Windows-only. The Tray UI is started with the console user's token so it runs on that user's desktop
(winsta0\\default) instead of in Session 0, where it would be invisible. WTSQueryUserToken only works for
LocalSystem, so this cannot be exercised from an ordinary shell.
The session SID is looked up from DOMAIN\\user because screen time maps SIDs, not user names, to children.
An empty SID means the lookup failed, and such a session is never matched to a child.
pywin32 does not export the WTS_SESSION_* codes of WM_WTSSESSION_CHANGE, so their fixed Windows values are
defined here.
"""

import sys
from pathlib import Path

import pywintypes
import win32con
import win32event
import win32process
import win32profile
import win32security
import win32ts

from service.core.bus import SessionEvent, SessionInfo

NO_SESSION = 0xFFFFFFFF
TRAY_EXE = "ogk-tray.exe"

WTS_SESSION_LOGON = 5
WTS_SESSION_LOGOFF = 6
WTS_SESSION_LOCK = 7
WTS_SESSION_UNLOCK = 8

EVENT_KINDS = {
    WTS_SESSION_LOGON: "logon",
    WTS_SESSION_LOGOFF: "logoff",
    WTS_SESSION_LOCK: "lock",
    WTS_SESSION_UNLOCK: "unlock",
}


def to_session_event(event_type: int, data) -> SessionEvent | None:
    kind = EVENT_KINDS.get(event_type)
    if kind is None:
        return None
    session_id = data[0] if isinstance(data, tuple) else int(data)
    return SessionEvent(kind, int(session_id))


def current_session() -> SessionInfo | None:
    session_id = win32ts.WTSGetActiveConsoleSessionId()
    if session_id == NO_SESSION:
        return None
    username = win32ts.WTSQuerySessionInformation(win32ts.WTS_CURRENT_SERVER_HANDLE, session_id, win32ts.WTSUserName)
    if not username:
        return None
    domain = win32ts.WTSQuerySessionInformation(win32ts.WTS_CURRENT_SERVER_HANDLE, session_id, win32ts.WTSDomainName)
    return SessionInfo(session_id, username, session_sid(domain, username))


def session_sid(domain: str, username: str) -> str:
    try:
        sid, _, _ = win32security.LookupAccountName(None, f"{domain}\\{username}" if domain else username)
    except pywintypes.error:
        return ""
    return win32security.ConvertSidToStringSid(sid)


class TrayProcess:
    def __init__(self, process_handle, pid: int) -> None:
        self._handle = process_handle
        self.pid = pid

    def alive(self) -> bool:
        return win32event.WaitForSingleObject(self._handle, 0) == win32event.WAIT_TIMEOUT

    def terminate(self) -> None:
        if self.alive():
            win32process.TerminateProcess(self._handle, 1)
            win32event.WaitForSingleObject(self._handle, 3000)


def tray_path() -> Path:
    return Path(sys.executable).with_name(TRAY_EXE)


def launch_tray(session_id: int) -> TrayProcess:
    token = win32ts.WTSQueryUserToken(session_id)
    try:
        environment = win32profile.CreateEnvironmentBlock(token, False)
        startup = win32process.STARTUPINFO()
        startup.lpDesktop = "winsta0\\default"
        exe = tray_path()
        process, thread, pid, _ = win32process.CreateProcessAsUser(
            token,
            str(exe),
            None,
            None,
            None,
            False,
            win32con.CREATE_UNICODE_ENVIRONMENT,
            environment,
            str(exe.parent),
            startup,
        )
    finally:
        token.Close()
    thread.Close()
    return TrayProcess(process, pid)
