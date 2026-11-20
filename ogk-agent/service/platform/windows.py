"""secure_path replaces the DACL with a protected one (no inherited ACEs): SYSTEM and Administrators get
full control. user_readable adds read for BUILTIN\\Users on that one file; users can still open it inside
the locked directory because Windows grants traverse checking bypass to everyone by default.
MachineGuid is read from the 64-bit registry view so a 32-bit build sees the same value.
SvcOtherEx runs on the SCM dispatcher thread, so session events are handed to the event loop thread.
"""

import asyncio
import hashlib
import logging
import os
import winreg
from collections.abc import Callable
from pathlib import Path

import ntsecuritycon
import servicemanager
import win32net
import win32netcon
import win32security
import win32service
import win32serviceutil
from win32com.shell import shell

from service.core.bus import SessionEvent
from service.core.logging_setup import setup_logging
from service.platform import Entry
from service.platform.process import list_processes, protected_dirs, read_chunks, terminate
from service.platform.session import current_session, launch_tray, to_session_event

__all__ = ["current_session", "launch_tray", "list_processes", "protected_dirs", "read_chunks", "terminate"]

log = logging.getLogger("ogk.platform")

SERVICE_NAME = "OGKAgent"

_entry: Entry | None = None
_listener: Callable[[SessionEvent], None] | None = None


def set_session_listener(listener: Callable[[SessionEvent], None] | None) -> None:
    global _listener
    _listener = listener


def data_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "OGK"


SID_SYSTEM = "S-1-5-18"
SID_ADMINISTRATORS = "S-1-5-32-544"
SID_USERS = "S-1-5-32-545"


def is_admin() -> bool:
    return bool(shell.IsUserAnAdmin())


def machine_fingerprint() -> str:
    access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, access) as key:
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
    return hashlib.sha256(str(guid).encode()).hexdigest()


def list_windows_accounts() -> list[tuple[str, str]]:
    accounts = []
    resume = 0
    while True:
        users, _, resume = win32net.NetUserEnum(None, 1, win32netcon.FILTER_NORMAL_ACCOUNT, resume)
        for user in users:
            if user["flags"] & win32netcon.UF_ACCOUNTDISABLE:
                continue
            sid, _, _ = win32security.LookupAccountName(None, user["name"])
            accounts.append((user["name"], win32security.ConvertSidToStringSid(sid)))
        if not resume:
            return accounts


def secure_path(path: Path, user_readable: bool = False) -> None:
    inherit = ntsecuritycon.OBJECT_INHERIT_ACE | ntsecuritycon.CONTAINER_INHERIT_ACE if path.is_dir() else 0
    dacl = win32security.ACL()
    for sid in (SID_SYSTEM, SID_ADMINISTRATORS):
        dacl.AddAccessAllowedAceEx(
            win32security.ACL_REVISION, inherit, ntsecuritycon.FILE_ALL_ACCESS, win32security.ConvertStringSidToSid(sid)
        )
    if user_readable:
        dacl.AddAccessAllowedAceEx(
            win32security.ACL_REVISION,
            0,
            ntsecuritycon.FILE_GENERIC_READ,
            win32security.ConvertStringSidToSid(SID_USERS),
        )
    win32security.SetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        dacl,
        None,
    )


class OGKService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = "OGK Agent Service"
    _svc_description_ = "OGK: helps parents manage their children's computer use"

    def __init__(self, args) -> None:
        super().__init__(args)
        self._loop = asyncio.new_event_loop()
        self._stop_event = asyncio.Event()

    def GetAcceptedControls(self) -> int:
        return super().GetAcceptedControls() | win32service.SERVICE_ACCEPT_SESSIONCHANGE

    def SvcOtherEx(self, control: int, event_type: int, data) -> None:
        if control != win32service.SERVICE_CONTROL_SESSIONCHANGE:
            return
        event = to_session_event(event_type, data)
        listener = _listener
        if event is not None and listener is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(listener, event)

    def SvcStop(self) -> None:
        log.info("stop requested by SCM")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._loop.call_soon_threadsafe(self._stop_event.set)

    def SvcDoRun(self) -> None:
        directory = data_dir()
        setup_logging(directory)
        log.info("service started, data dir %s", directory)
        try:
            self._loop.run_until_complete(_entry(directory, self._stop_event))
        except Exception:
            log.exception("service crashed")
            logging.shutdown()
            os._exit(1)
        finally:
            self._loop.close()
        log.info("service stopped")


def run_service(argv: list[str], entry: Entry) -> None:
    global _entry
    _entry = entry
    if len(argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(OGKService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(OGKService, argv=argv)
