"""secure_path replaces the DACL with a protected one (no inherited ACEs): SYSTEM and Administrators get
full control. user_readable adds read for BUILTIN\\Users on that one file; users can still open it inside
the locked directory because Windows grants traverse checking bypass to everyone by default.
MachineGuid is read from the 64-bit registry view so a 32-bit build sees the same value.
SvcOtherEx runs on the SCM dispatcher thread, so session events are handed to the event loop thread.
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
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


def _netsh(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["netsh.exe", *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=15,
    )
    return result.stdout.strip()


def _dns_interfaces(family: str) -> list[dict]:
    output = _netsh("interface", family, "show", "dnsservers")
    interfaces: list[dict] = []
    current: dict | None = None
    for line in output.splitlines():
        match = re.search(r'Configuration for interface "(.+)"', line)
        if match:
            current = {"name": match.group(1), "family": family, "source": None, "servers": []}
            interfaces.append(current)
            continue
        if current is None:
            continue
        if "Statically Configured DNS Servers:" in line:
            current["source"] = "static"
            value = line.split(":", 1)[1].strip()
        elif "DNS servers configured through DHCP:" in line:
            current["source"] = "dhcp"
            value = line.split(":", 1)[1].strip()
        else:
            value = line.strip()
            if not value or value.startswith("Register with") or value == "None":
                continue
            if current["source"] is None:
                continue
        if value and value != "None":
            current["servers"].append(value)
    return [item for item in interfaces if item["source"]]


def _set_dns(item: dict, *, source: str, address: str | None = None) -> None:
    args = ["interface", item["family"], "set", "dnsservers", f"name={item['name']}", f"source={source}"]
    if address is not None:
        args.append(f"address={address}")
    args.append("validate=no")
    _netsh(*args)


def configure_dns(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "dns_config.json"
    if path.exists():
        entries = json.loads(path.read_text(encoding="utf-8"))
    else:
        entries = _dns_interfaces("ipv4") + _dns_interfaces("ipv6")
        path.write_text(json.dumps(entries), encoding="utf-8")
    for entry in entries:
        if "Loopback Pseudo-Interface" in entry["name"]:
            continue
        proxy = "127.0.0.1" if entry["family"] == "ipv4" else "::1"
        _set_dns(entry, source="static", address=proxy)


def restore_dns(directory: Path) -> None:
    path = directory / "dns_config.json"
    if not path.exists():
        return
    entries = json.loads(path.read_text(encoding="utf-8"))
    for entry in entries:
        if "Loopback Pseudo-Interface" in entry["name"]:
            continue
        # Older builds could persist the proxy itself (127.0.0.1/::1) in the
        # snapshot. Never restore those values as the machine's upstream DNS.
        servers = [server for server in entry.get("servers", []) if server.split("%", 1)[0] not in {"127.0.0.1", "::1"}]
        if entry["source"] == "dhcp" or (entry.get("servers") and not servers):
            _set_dns(entry, source="dhcp")
        elif servers:
            _set_dns(entry, source="static", address=servers[0])
            for index, server in enumerate(servers[1:], 2):
                _netsh(
                    "interface",
                    entry["family"],
                    "add",
                    "dnsservers",
                    f"name={entry['name']}",
                    f"address={server}",
                    f"index={index}",
                    "validate=no",
                )
        else:
            _set_dns(entry, source="static", address="none")
    path.unlink(missing_ok=True)


def configure_firewall(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    restore_firewall(directory)
    for protocol in ("UDP", "TCP"):
        _netsh(
            "advfirewall",
            "firewall",
            "add",
            "rule",
            "name=OGK Web Filter DNS block " + protocol,
            "dir=out",
            "action=block",
            f"protocol={protocol}",
            "remoteport=53,853",
            "profile=any",
            "enable=yes",
        )
    _netsh(
        "advfirewall",
        "firewall",
        "add",
        "rule",
        "name=OGK Web Filter DNS agent",
        "dir=out",
        "action=allow",
        f"program={sys.executable}",
        "protocol=UDP",
        "remoteport=53,853",
        "profile=any",
        "enable=yes",
    )
    (directory / "firewall_config.json").write_text('{"configured":true}', encoding="utf-8")


def restore_firewall(directory: Path) -> None:
    for name in (
        "OGK Web Filter DNS block UDP",
        "OGK Web Filter DNS block TCP",
        "OGK Web Filter DNS agent",
    ):
        _netsh("advfirewall", "firewall", "delete", "rule", f"name={name}", check=False)
    (directory / "firewall_config.json").unlink(missing_ok=True)


def disable_doh(directory: Path) -> None:
    path = directory / "doh_config.json"
    policy_keys = (
        (r"SOFTWARE\Policies\Google\Chrome", "DnsOverHttpsMode"),
        (r"SOFTWARE\Policies\Microsoft\Edge", "DnsOverHttpsMode"),
    )
    if not path.exists():
        values = {}
        for key_path, name in policy_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
                    values[key_path] = winreg.QueryValueEx(key, name)[0]
            except FileNotFoundError:
                values[key_path] = None
        path.write_text(json.dumps(values), encoding="utf-8")
    for key_path, name in policy_keys:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, "off")


def restore_doh(directory: Path) -> None:
    path = directory / "doh_config.json"
    if not path.exists():
        return
    values = json.loads(path.read_text(encoding="utf-8"))
    for key_path, name in (
        (r"SOFTWARE\Policies\Google\Chrome", "DnsOverHttpsMode"),
        (r"SOFTWARE\Policies\Microsoft\Edge", "DnsOverHttpsMode"),
    ):
        value = values.get(key_path)
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if value is None:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, name)
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    path.unlink(missing_ok=True)


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
