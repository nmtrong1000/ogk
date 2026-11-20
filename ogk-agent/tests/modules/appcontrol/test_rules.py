from service.core.process_info import ProcInfo
from service.modules.appcontrol.rules import ALLOW, BLOCK, blocked_by_name, decide, is_protected

NOTEPAD_SHA = "a" * 64
GAME_SHA = "b" * 64
WINDOWS = ["C:\\Windows", "C:\\Windows\\System32", "C:\\Windows\\SystemApps\\*"]


def rule(name: str, action: str = BLOCK, sha256: str | None = None) -> dict:
    return {"name": name, "action": action, "sha256": sha256}


def proc(name: str, exe: str, session_id: int | None = 1, pid: int = 500) -> ProcInfo:
    return ProcInfo(pid, 1.0, name, exe, session_id)


def test_block_by_name():
    assert decide("game.exe", None, [rule("game.exe")]) == BLOCK
    assert decide("other.exe", None, [rule("game.exe")]) == ALLOW


def test_renamed_exe_blocked_by_hash():
    rules = [rule("notepad.exe", sha256=NOTEPAD_SHA)]
    assert decide("game.exe", NOTEPAD_SHA, rules) == BLOCK
    assert decide("game.exe", GAME_SHA, rules) == ALLOW


def test_hash_rule_still_blocks_by_name():
    assert decide("notepad.exe", GAME_SHA, [rule("notepad.exe", sha256=NOTEPAD_SHA)]) == BLOCK


def test_allow_by_hash_overrides_block():
    rules = [rule("game.exe"), rule("game.exe", ALLOW, GAME_SHA)]
    assert decide("game.exe", GAME_SHA, rules) == ALLOW
    assert decide("game.exe", NOTEPAD_SHA, rules) == BLOCK


def test_allow_by_name_alone_never_overrides():
    rules = [rule("notepad.exe", sha256=NOTEPAD_SHA), rule("game.exe", ALLOW)]
    assert decide("game.exe", NOTEPAD_SHA, rules) == BLOCK


def test_name_block_waits_when_allow_by_hash_exists():
    assert blocked_by_name("game.exe", [rule("game.exe")])
    assert not blocked_by_name("game.exe", [rule("game.exe"), rule("x.exe", ALLOW, GAME_SHA)])


def test_system_process_under_windows_is_protected():
    assert is_protected(proc("explorer.exe", "C:\\Windows\\explorer.exe"), 1, WINDOWS)
    assert is_protected(proc("svchost.exe", "c:\\windows\\System32\\svchost.exe"), 1, WINDOWS)


def test_renamed_explorer_outside_windows_is_not_protected():
    assert not is_protected(proc("explorer.exe", "C:\\Users\\An\\Downloads\\explorer.exe"), 1, WINDOWS)
    assert not is_protected(proc("explorer.exe", "C:\\WindowsGames\\explorer.exe"), 1, WINDOWS)


def test_system_app_folder_is_protected():
    path = "C:\\WINDOWS\\SystemApps\\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\\SearchHost.exe"
    assert is_protected(proc("searchhost.exe", path), 1, WINDOWS)


def test_user_writable_folders_under_windows_are_not_protected():
    for folder in ("Temp", "Tasks", "tracing", "System32\\spool\\drivers\\color", "SystemApps\\App\\sub"):
        exe = f"C:\\Windows\\{folder}\\explorer.exe"
        assert not is_protected(proc("explorer.exe", exe), 1, WINDOWS), folder


def test_unreadable_system_name_is_protected():
    assert is_protected(proc("csrss.exe", ""), 1, WINDOWS)


def test_other_session_and_system_pids_are_protected():
    assert is_protected(proc("game.exe", "C:\\game.exe", session_id=0), 1, WINDOWS)
    assert is_protected(proc("game.exe", "C:\\game.exe", session_id=None), 1, WINDOWS)
    assert is_protected(proc("system", "", pid=4), 1, WINDOWS)
    assert not is_protected(proc("game.exe", "C:\\game.exe"), 1, WINDOWS)
