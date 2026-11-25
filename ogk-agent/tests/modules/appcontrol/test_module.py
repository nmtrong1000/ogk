import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from service.core.app_state import AppState
from service.core.bus import SESSION, TRAY_HEARTBEAT, Bus, SessionEvent, SessionInfo, TrayPing
from service.core.enforcement import Enforcement
from service.core.event_queue import EventQueue
from service.core.local_db import DB_FILE, LocalDb
from service.core.policy_store import PolicyStore
from service.core.process_info import ProcInfo
from service.core.screen_state import ScreenState
from service.core.trusted_clock import TrustedClock
from service.modules.appcontrol import AppControlModule
from service.modules.appcontrol.hashing import HashCache
from tests.core.test_default_policy import DEFAULT
from tests.policy_vectors import body, document, write_public_key

pytestmark = pytest.mark.anyio

SID = "S-1-5-21-1000-1000-1000-1001"
PARENT_SID = "S-1-5-21-1000-1000-1000-1500"
START = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)


class FakePlatform:
    def __init__(self, root) -> None:
        self.user: SessionInfo | None = SessionInfo(1, "an", SID)
        self.root = root
        self.processes: list[ProcInfo] = []
        self.killed: list[str] = []
        self.next_pid = 1000

    def current_session(self) -> SessionInfo | None:
        return self.user

    def list_processes(self) -> list[ProcInfo]:
        return list(self.processes)

    def terminate(self, pid: int, create_time: float) -> bool:
        match = [p for p in self.processes if (p.pid, p.create_time) == (pid, create_time)]
        if not match:
            return False
        self.processes.remove(match[0])
        self.killed.append(match[0].name)
        return True

    def protected_dirs(self) -> list[str]:
        return [str(self.root / "Windows"), str(self.root / "Windows" / "System32")]

    def launch(self, name: str, content: bytes = b"", folder: str = "Users", session_id: int = 1) -> ProcInfo:
        path = self.root / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content or name.encode())
        self.next_pid += 1
        proc = ProcInfo(self.next_pid, float(self.next_pid), name.lower(), str(path), session_id)
        self.processes.append(proc)
        return proc


class FakeDevice:
    device_id = 3


class Rig:
    def __init__(self, data_dir) -> None:
        self.data_dir = data_dir
        self.mono = 1000.0
        self.wall = START
        self.db = LocalDb(data_dir)
        self.store = PolicyStore(self.db, write_public_key(data_dir), DEFAULT)
        self.bus = Bus()
        self.platform = FakePlatform(data_dir / "disk")
        self.apps = AppState()
        self.enforcement = Enforcement()
        self.screen = ScreenState()
        self.hashes = HashCache()
        self.clock = TrustedClock(self.db, lambda: self.mono, lambda: self.wall, tz=UTC)
        self.module = AppControlModule(
            self.store,
            self.clock,
            self.apps,
            self.enforcement,
            self.bus,
            self.platform,
            EventQueue(self.db, None),
            FakeDevice(),
            self.screen,
            self.hashes,
            monotonic=lambda: self.mono,
        )

    def policy(self, app_rules: list[dict], version: int = 1, accounts: list[str] | None = None) -> None:
        doc = document(7, version, accounts=[SID] if accounts is None else accounts, app_rules=app_rules)
        self.store.save(body(doc))

    async def start(self) -> None:
        self.clock.load()
        self.module.start()
        await self.module.tick()

    async def run(self, seconds: int) -> None:
        for _ in range(seconds):
            self.mono += 1
            self.wall += timedelta(seconds=1)
            await self.module.tick()

    async def use(self, foreground: str | None, seconds: int, idle: float = 0.0) -> None:
        for _ in range(seconds):
            self.ping(foreground, idle)
            await self.run(1)

    def ping(self, foreground: str | None, idle: float = 0.0) -> None:
        self.bus.publish(TRAY_HEARTBEAT, TrayPing(4242, idle, foreground))

    def session(self, kind: str) -> None:
        self.bus.publish(SESSION, SessionEvent(kind, 1))

    def events(self) -> list[dict]:
        with sqlite3.connect(self.data_dir / DB_FILE) as conn:
            rows = conn.execute("SELECT payload FROM event_outbox ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]

    def kinds(self) -> list[tuple]:
        return [(e["type"], e["subject"], e["duration_sec"]) for e in self.events()]


def block(name: str, sha256: str | None = None) -> dict:
    return {"name": name, "sha256": sha256, "action": "block"}


@pytest.fixture
def rig(data_dir):
    return Rig(data_dir)


async def test_blocked_name_is_killed_with_event_and_tray_notice(rig):
    rig.policy([block("game.exe")])
    await rig.start()
    rig.platform.launch("game.exe")
    rig.platform.launch("notes.exe")
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]
    assert (rig.apps.block_seq, rig.apps.app, rig.apps.set_by, rig.apps.source) == (
        1,
        "game.exe",
        "parent@example.com",
        "cached",
    )
    (event,) = rig.events()
    assert (event["type"], event["subject"], event["child_id"], event["policy_id"]) == ("blocked_app", "game.exe", 7, 1)


async def test_exhausted_group_budget_closes_an_already_running_app(rig):
    groups = [
        {"id": "education", "name": "Học tập", "budget_minutes": None},
        {"id": "entertainment", "name": "Giải trí", "budget_minutes": None},
        {"id": "social", "name": "Mạng xã hội", "budget_minutes": None},
        {"id": "games", "name": "Trò chơi", "budget_minutes": 0},
        {"id": "adult", "name": "Người lớn", "budget_minutes": None},
        {"id": "unclassified", "name": "Chưa phân loại", "budget_minutes": None},
    ]
    rules = [{"name": "game.exe", "sha256": None, "action": "allow", "group_id": "games"}]
    rig.store.save(body(document(7, 1, accounts=[SID], app_rules=rules, app_groups=groups)))
    rig.screen.group_remaining = [{"group_id": "games", "name": "Trò chơi", "remaining_seconds": 0}]
    await rig.start()
    rig.platform.launch("game.exe")
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]
    assert rig.apps.reason == "group_budget:Trò chơi"


async def test_another_group_stays_available_after_budget_expires(rig):
    groups = [
        {"id": "education", "name": "Học tập", "budget_minutes": None},
        {"id": "entertainment", "name": "Giải trí", "budget_minutes": None},
        {"id": "social", "name": "Mạng xã hội", "budget_minutes": None},
        {"id": "games", "name": "Trò chơi", "budget_minutes": 45},
        {"id": "adult", "name": "Người lớn", "budget_minutes": None},
        {"id": "unclassified", "name": "Chưa phân loại", "budget_minutes": None},
    ]
    rules = [
        {"name": "game.exe", "sha256": None, "action": "allow", "group_id": "games"},
        {"name": "word.exe", "sha256": None, "action": "allow", "group_id": "education"},
    ]
    rig.store.save(body(document(7, 1, accounts=[SID], app_rules=rules, app_groups=groups)))
    rig.screen.group_remaining = [
        {"group_id": "games", "name": "Trò chơi", "remaining_seconds": 0},
        {"group_id": "education", "name": "Học tập", "remaining_seconds": None},
    ]
    await rig.start()
    rig.platform.launch("game.exe")
    rig.platform.launch("word.exe")
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]
    assert [proc.name for proc in rig.platform.processes] == ["word.exe"]


async def test_renamed_notepad_is_blocked_by_hash(rig):
    notepad = b"notepad binary"
    rig.policy([block("notepad.exe", hashlib.sha256(notepad).hexdigest())])
    await rig.start()
    rig.platform.launch("game.exe", notepad)
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]
    assert rig.events()[0]["subject"] == "game.exe"


async def test_allow_by_hash_lets_exact_build_run(rig):
    good = b"approved build"
    rig.policy([block("game.exe"), {"name": "game.exe", "sha256": hashlib.sha256(good).hexdigest(), "action": "allow"}])
    await rig.start()
    rig.platform.launch("game.exe", good, folder="a")
    rig.platform.launch("game.exe", b"other build", folder="b")
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]
    assert len(rig.platform.processes) == 1


async def test_system_processes_never_killed(rig):
    rig.policy([block("explorer.exe"), block("svchost.exe"), block("game.exe")])
    await rig.start()
    rig.platform.launch("explorer.exe", folder="Windows")
    rig.platform.launch("svchost.exe", folder="Windows/System32")
    rig.platform.launch("game.exe", session_id=0)
    await rig.run(1)
    assert rig.platform.killed == []
    renamed = rig.platform.launch("explorer.exe", b"game", folder="Users/An/Downloads")
    await rig.run(1)
    assert rig.platform.killed == ["explorer.exe"]
    assert renamed not in rig.platform.processes


async def test_protected_name_in_writable_windows_folder_is_checked(rig):
    game = b"game binary"
    rig.policy([block("game.exe", hashlib.sha256(game).hexdigest())])
    await rig.start()
    rig.platform.launch("explorer.exe", game, folder="Windows/Temp")
    await rig.run(1)
    assert rig.platform.killed == ["explorer.exe"]


async def test_unhashable_exe_is_blocked_when_policy_has_hash_rules(rig, caplog):
    rig.policy([block("game.exe", "c" * 64)])
    await rig.start()
    launched = rig.platform.launch("renamed.exe", b"game")
    Path(launched.exe).unlink()
    await rig.run(1)
    assert rig.platform.killed == ["renamed.exe"]
    assert "cannot hash renamed.exe" in caplog.text


async def test_unhashable_exe_runs_when_policy_has_only_name_rules(rig):
    rig.policy([block("game.exe")])
    await rig.start()
    launched = rig.platform.launch("other.exe", b"x")
    Path(launched.exe).unlink()
    await rig.run(1)
    assert rig.platform.killed == []


async def test_no_kill_while_enforcement_disabled(rig):
    rig.policy([block("game.exe")])
    await rig.start()
    rig.enforcement.disable("tray_unavailable")
    rig.platform.launch("game.exe")
    await rig.run(2)
    assert rig.platform.killed == []
    rig.enforcement.enable()
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]


async def test_parent_session_is_not_enforced(rig):
    rig.policy([block("game.exe")])
    rig.platform.user = SessionInfo(1, "bo", PARENT_SID)
    await rig.start()
    rig.platform.launch("game.exe")
    await rig.run(1)
    assert rig.platform.killed == []


async def test_new_rule_applies_to_running_app(rig):
    rig.policy([])
    await rig.start()
    rig.platform.launch("game.exe")
    await rig.run(1)
    assert rig.platform.killed == []
    rig.policy([block("game.exe")], version=2)
    await rig.run(1)
    assert rig.platform.killed == ["game.exe"]


async def test_relaunch_storm_throttles_events_not_notices(rig):
    rig.policy([block("game.exe")])
    await rig.start()
    for _ in range(3):
        rig.platform.launch("game.exe")
        await rig.run(1)
    assert rig.platform.killed == ["game.exe"] * 3
    assert rig.apps.block_seq == 3
    assert [e["type"] for e in rig.events()] == ["blocked_app"]
    await rig.run(5)
    rig.platform.launch("game.exe")
    await rig.run(1)
    assert [e["type"] for e in rig.events()] == ["blocked_app", "blocked_app"]


async def test_unchanged_exe_is_hashed_once(rig):
    rig.policy([block("x.exe", "0" * 64)])
    await rig.start()
    first = rig.platform.launch("tool.exe")
    await rig.run(1)
    rig.platform.processes = [ProcInfo(first.pid + 10, first.create_time + 10, first.name, first.exe, 1)]
    await rig.run(1)
    assert rig.hashes.computed == 1


async def test_foreground_app_time_is_recorded(rig):
    rig.policy([])
    await rig.start()
    await rig.use("chrome.exe", 30)
    await rig.use("word.exe", 10)
    await rig.use(None, 1)
    assert rig.kinds() == [
        ("app_start", "chrome.exe", 0),
        ("app_stop", "chrome.exe", 30),
        ("app_start", "word.exe", 0),
        ("app_stop", "word.exe", 10),
    ]


async def test_background_app_gets_no_time(rig):
    rig.policy([])
    await rig.start()
    rig.platform.launch("music.exe")
    await rig.use("chrome.exe", 20)
    assert {e["subject"] for e in rig.events()} == {"chrome.exe"}


async def test_idle_lock_and_quiet_tray_stop_the_interval(rig):
    rig.policy([])
    await rig.start()
    await rig.use("chrome.exe", 5)
    await rig.use("chrome.exe", 1, idle=301)
    await rig.use("chrome.exe", 4)
    rig.session("lock")
    await rig.use("chrome.exe", 1)
    rig.session("unlock")
    await rig.use("chrome.exe", 3)
    await rig.run(16)
    assert rig.kinds() == [
        ("app_start", "chrome.exe", 0),
        ("app_stop", "chrome.exe", 5),
        ("app_start", "chrome.exe", 0),
        ("app_stop", "chrome.exe", 4),
        ("app_start", "chrome.exe", 0),
        ("app_stop", "chrome.exe", 17),
    ]


async def test_no_app_time_for_parent_session(rig):
    rig.policy([])
    rig.platform.user = SessionInfo(1, "bo", PARENT_SID)
    await rig.start()
    await rig.use("chrome.exe", 5)
    assert rig.events() == []


async def test_long_interval_is_split_at_one_day(rig):
    rig.policy([])
    await rig.start()
    rig.ping("chrome.exe")
    await rig.run(1)
    rig.mono += 86400
    rig.ping("chrome.exe")
    await rig.module.tick()
    assert rig.kinds()[:3] == [
        ("app_start", "chrome.exe", 0),
        ("app_stop", "chrome.exe", 86400),
        ("app_start", "chrome.exe", 0),
    ]
