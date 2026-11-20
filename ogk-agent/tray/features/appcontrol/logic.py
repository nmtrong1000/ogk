"""Pure decisions from /ipc/appcontrol snapshots, kept free of Tk so they run in tests.
The first snapshot only sets the baseline, so a restarted Tray UI does not explain a block it never saw.
A new run_id means the service restarted and block_seq started again at 0, so any block in that run is new.
"""

from dataclasses import dataclass
from typing import Any

TITLE = "OGK - Ứng dụng bị chặn"
DEFAULT_SETTER = "Phụ huynh"
DEFAULT_POLICY_SETTER = "Chính sách mặc định (máy mất kết nối với server)"


@dataclass(frozen=True)
class BlockNotice:
    seq: int
    text: str


def setter_text(snapshot: dict[str, Any]) -> str:
    if snapshot.get("set_by"):
        return snapshot["set_by"]
    if snapshot.get("source") == "default":
        return DEFAULT_POLICY_SETTER
    return DEFAULT_SETTER


def notice_text(snapshot: dict[str, Any]) -> str:
    app = snapshot.get("app") or "ứng dụng"
    return (
        f"Ứng dụng {app} đã bị đóng vì nằm trong danh sách ứng dụng bị chặn.\n"
        f"Người đặt luật: {setter_text(snapshot)}.\n"
        "Nếu con nghĩ đây là nhầm lẫn, hãy nói với phụ huynh."
    )


class BlockTracker:
    def __init__(self) -> None:
        self._seq: int | None = None
        self._run: Any = None

    def update(self, snapshot: dict[str, Any]) -> BlockNotice | None:
        seq = snapshot.get("block_seq")
        if not isinstance(seq, int) or isinstance(seq, bool):
            return None
        run = snapshot.get("run_id")
        previous, previous_run = self._seq, self._run
        self._seq, self._run = seq, run
        if previous is None:
            return None
        if run != previous_run:
            return BlockNotice(seq, notice_text(snapshot)) if seq > 0 else None
        if seq <= previous:
            return None
        return BlockNotice(seq, notice_text(snapshot))
