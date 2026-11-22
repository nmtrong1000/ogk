from dataclasses import dataclass
from typing import Any

TITLE = "OGK - Website bị chặn"


@dataclass(frozen=True)
class BlockNotice:
    seq: int
    text: str


def notice_text(snapshot: dict[str, Any]) -> str:
    setter = snapshot.get("set_by") or "Phụ huynh"
    reason = snapshot.get("reason") or "theo chính sách gia đình"
    return f"Tên miền {snapshot.get('domain') or 'website'} đã bị chặn.\nLý do: {reason}.\nNgười đặt luật: {setter}."


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
            return BlockNotice(seq, notice_text(snapshot)) if seq else None
        return BlockNotice(seq, notice_text(snapshot)) if seq > previous else None
