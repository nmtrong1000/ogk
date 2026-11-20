"""An allow rule only counts when it names a SHA-256: an allow by name alone could be bypassed by renaming any
exe, so it is kept as a note and never overrides a block.
A protected name is trusted only when its exe sits directly in a protected directory, never deeper: standard
users can create files in subfolders such as C:\\Windows\\Temp, Tasks or System32\\spool\\drivers\\color, so a
game copied there as explorer.exe is still checked. A directory ending in \\* trusts its direct subfolders
(SystemApps\\<app>). An exe path that cannot be read is treated as protected, because only system processes
deny LocalSystem.
"""

from service.core.process_info import ProcInfo

BLOCK = "block"
ALLOW = "allow"
SYSTEM_PIDS = frozenset({0, 4})
PROTECTED_NAMES = frozenset(
    {
        "system",
        "registry",
        "memory compression",
        "secure system",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
        "lsaiso.exe",
        "svchost.exe",
        "dwm.exe",
        "explorer.exe",
        "sihost.exe",
        "fontdrvhost.exe",
        "ctfmon.exe",
        "taskhostw.exe",
        "runtimebroker.exe",
        "logonui.exe",
        "lockapp.exe",
        "userinit.exe",
        "conhost.exe",
        "dllhost.exe",
        "searchhost.exe",
        "startmenuexperiencehost.exe",
        "shellexperiencehost.exe",
        "applicationframehost.exe",
        "textinputhost.exe",
        "securityhealthservice.exe",
        "securityhealthsystray.exe",
        "msmpeng.exe",
        "nissrv.exe",
        "spoolsv.exe",
        "audiodg.exe",
        "wudfhost.exe",
        "ogk-service.exe",
        "ogk-tray.exe",
    }
)


def _normalize(path: str) -> str:
    return path.replace("/", "\\").lower().rstrip("\\")


def _directly_in(exe: str, directory: str) -> bool:
    parent = _normalize(exe).rpartition("\\")[0]
    base = _normalize(directory)
    if base.endswith("\\*"):
        root = base[:-2]
        return parent.startswith(root + "\\") and "\\" not in parent[len(root) + 1 :]
    return parent == base


def is_protected(proc: ProcInfo, child_session: int, protected_dirs: list[str]) -> bool:
    if proc.pid in SYSTEM_PIDS or proc.session_id != child_session:
        return True
    if proc.name not in PROTECTED_NAMES:
        return False
    return not proc.exe or any(_directly_in(proc.exe, d) for d in protected_dirs)


def has_hash_rules(app_rules: list[dict]) -> bool:
    return any(rule["sha256"] is not None for rule in app_rules)


def blocked_by_name(name: str, app_rules: list[dict]) -> bool:
    if any(rule["action"] == ALLOW and rule["sha256"] is not None for rule in app_rules):
        return False
    return any(rule["action"] == BLOCK and rule["name"] == name for rule in app_rules)


def decide(name: str, sha256: str | None, app_rules: list[dict]) -> str:
    if sha256 is not None and any(r["action"] == ALLOW and r["sha256"] == sha256 for r in app_rules):
        return ALLOW
    for rule in app_rules:
        if rule["action"] != BLOCK:
            continue
        if rule["name"] == name or (sha256 is not None and rule["sha256"] == sha256):
            return BLOCK
    return ALLOW
