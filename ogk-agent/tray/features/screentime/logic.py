"""Pure decisions from /ipc/screentime snapshots, kept free of Tk so they run in tests.
The first snapshot only sets the warning baseline, so a restarted Tray UI does not replay old warnings, but a
locked state with an unseen lock_seq is always obeyed, because a restarted Tray UI must still lock the session.
"""

from dataclasses import dataclass
from typing import Any

REASON_TEXT = {
    "quota": "Đã hết thời gian dùng máy hôm nay.",
    "schedule": "Bây giờ nằm ngoài khung giờ được dùng máy.",
}
DEFAULT_SETTER = "Phụ huynh"
WARNING_TITLE = "Sắp hết giờ dùng máy"
REMAINING_TITLE = "OGK - Thời gian còn lại"


@dataclass(frozen=True)
class LockOrder:
    seq: int
    text: str


@dataclass(frozen=True)
class Plan:
    remaining: str
    notify: tuple[str, str] | None = None
    grace: str | None = None
    lock: LockOrder | None = None


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def tray_tooltip_text(base: str, remaining: str) -> str:
    summary = remaining.split("\n\n", 1)[0]
    return f"{base}\n{summary}"[:127]


def remaining_text(snapshot: dict[str, Any]) -> str:
    state = snapshot.get("state")
    if snapshot.get("child_id") is None or state == "none":
        result = "Không có giới hạn thời gian cho tài khoản này."
    elif snapshot.get("override"):
        result = "Được phụ huynh mở khóa đến hết ngày hôm nay."
    elif state == "locked":
        result = "Đã hết giờ dùng máy."
    elif state == "grace":
        result = f"Đã hết giờ. Máy sẽ khóa sau {snapshot.get('grace_seconds') or 0} giây."
    else:
        result = f"Còn lại {format_duration(snapshot.get('remaining_seconds') or 0)}"
    groups = snapshot.get("group_remaining", [])
    if groups:
        lines = ["Thời gian theo nhóm ứng dụng:"]
        for group in groups:
            remaining = group.get("remaining_seconds")
            value = "Không giới hạn" if remaining is None else format_duration(remaining)
            lines.append(f"{group.get('name', 'Nhóm')}: {value}")
        result += "\n\n" + "\n".join(lines)
    return result


def warning_message(minutes: int) -> str:
    return f"Còn {minutes} phút dùng máy. Hãy lưu bài đang làm."


def grace_text(snapshot: dict[str, Any]) -> str:
    reason = REASON_TEXT.get(snapshot.get("lock_reason") or "", "Đã hết giờ dùng máy.")
    return f"{reason}\nMáy sẽ khóa sau {snapshot.get('grace_seconds') or 0} giây. Hãy lưu bài ngay."


def lock_text(snapshot: dict[str, Any]) -> str:
    reason = REASON_TEXT.get(snapshot.get("lock_reason") or "", "Máy bị khóa theo luật của phụ huynh.")
    setter = snapshot.get("set_by") or DEFAULT_SETTER
    return f"{reason}\nNgười đặt luật: {setter}\nMáy sẽ khóa ngay bây giờ."


class Tracker:
    def __init__(self) -> None:
        self._warning_seq: int | None = None
        self._lock_seq: int | None = None
        self._command_seq: int | None = None

    def update(self, snapshot: dict[str, Any]) -> Plan:
        notify = None
        warning_seq = snapshot.get("warning_seq") or 0
        if self._warning_seq is not None and warning_seq > self._warning_seq and snapshot.get("warning"):
            notify = (WARNING_TITLE, warning_message(snapshot["warning"]))
        self._warning_seq = warning_seq
        lock = None
        command_seq = snapshot.get("command_seq") or 0
        if self._command_seq is not None and command_seq > self._command_seq:
            kind = snapshot.get("command_type")
            messages = {
                "lock": ("Phụ huynh khóa máy", "Phụ huynh vừa gửi lệnh khóa máy."),
                "unlock": ("Phụ huynh mở khóa máy", "Phụ huynh đã mở khóa máy cho bạn."),
                "add_time": ("Được cộng thêm thời gian", "Phụ huynh đã cộng 15 phút sử dụng máy."),
            }
            notify = messages.get(kind)
        self._command_seq = command_seq
        lock_seq = snapshot.get("lock_seq") or 0
        if snapshot.get("state") == "locked" and lock_seq != self._lock_seq:
            lock = LockOrder(lock_seq, lock_text(snapshot))
        self._lock_seq = lock_seq
        grace = grace_text(snapshot) if snapshot.get("state") == "grace" else None
        return Plan(remaining_text(snapshot), notify, grace, lock)
