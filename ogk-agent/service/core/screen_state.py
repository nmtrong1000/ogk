"""The screen-time module writes this state every tick and the IPC route hands a snapshot to the Tray UI.
warning_seq and lock_seq only grow: the Tray UI acts once per new value, so a repeated poll never shows the
same warning twice, and a new lock_seq is a fresh order to lock even when state was already locked.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

STATE_NONE = "none"
STATE_OK = "ok"
STATE_GRACE = "grace"
STATE_LOCKED = "locked"


@dataclass
class ScreenState:
    child_id: int | None = None
    state: str = STATE_NONE
    counting: bool = False
    used_seconds: int = 0
    quota_seconds: int | None = None
    remaining_seconds: int | None = None
    warning: int | None = None
    warning_seq: int = 0
    grace_seconds: int | None = None
    lock_reason: str | None = None
    lock_seq: int = 0
    set_by: str = ""
    override: bool = False
    command_seq: int = 0
    command_type: str | None = None
    used_today: dict[int, int] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("used_today")
        return data
