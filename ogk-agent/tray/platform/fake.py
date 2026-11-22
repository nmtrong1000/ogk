"""Fake tray platform for macOS. pystray and Tk both need the main thread, so pystray shares the Tk run loop.
Notifications go through osascript because pystray's macOS backend does not show them for an unbundled
Python process.
idle_seconds reads <data>/fake_idle (a number of seconds, 0 when missing) so idle time can be simulated with
`echo 400 > .ogk-data/fake_idle`. lock_workstation records each order in fake_lock.jsonl and appends a "lock"
line to fake_session.jsonl in the format of the service's fake platform, so the service sees the session
locked just as SESSIONCHANGE would report it on Windows.
foreground_app reads <data>/fake_foreground (an exe name; missing or empty means no foreground window), e.g.
`echo chrome.exe > .ogk-data/fake_foreground`.
"""

import contextlib
import json
import os
import subprocess
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path

import pystray

IDLE_FILE = "fake_idle"
FOREGROUND_FILE = "fake_foreground"
LOCK_FILE = "fake_lock.jsonl"
SESSION_FILE = "fake_session.jsonl"
FAKE_SESSION_ID = 1


def data_dir() -> Path:
    return Path(os.environ.get("OGK_DATA_DIR", ".ogk-data")).resolve()


def idle_seconds() -> float:
    try:
        return max(0.0, float((data_dir() / IDLE_FILE).read_text(encoding="utf-8").strip()))
    except (OSError, ValueError):
        return 0.0


def foreground_app() -> str | None:
    try:
        name = (data_dir() / FOREGROUND_FILE).read_text(encoding="utf-8").strip().lower()
    except OSError:
        return None
    return name or None


def _append(name: str, record: dict) -> None:
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / name).open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def lock_workstation() -> bool:
    _append(LOCK_FILE, {"ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
    _append(SESSION_FILE, {"event": "lock", "session_id": FAKE_SESSION_ID})
    return True


def run_tray(icon: pystray.Icon, root: tk.Tk) -> None:
    icon.run_detached()
    root.mainloop()


def acquire_single_instance() -> bool:
    return True


def _quote(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def notify(icon: pystray.Icon, title: str, message: str) -> None:
    script = f"display notification {_quote(message)} with title {_quote(title)}"
    with contextlib.suppress(OSError):
        subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
