from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Decision:
    request_id: int
    text: str


def decision_text(item: dict[str, Any]) -> str:
    result = "được duyệt" if item.get("status") == "approved" else "chưa được duyệt"
    kind = "thêm giờ" if item.get("type") == "add_time" else f"mở chặn {item.get('domain') or 'website'}"
    message = item.get("message")
    suffix = f"\nLời nhắn của phụ huynh: {message}" if message else ""
    return f"Yêu cầu {kind} {result}.{suffix}"


class DecisionTracker:
    def __init__(self) -> None:
        self._seen: set[int] | None = None

    def update(self, items: list[dict[str, Any]]) -> list[Decision]:
        valid = {item["id"]: item for item in items if isinstance(item, dict) and isinstance(item.get("id"), int)}
        if self._seen is None:
            self._seen = set(valid)
            latest = valid[max(valid)] if valid else None
            return [] if latest is None else [Decision(latest["id"], decision_text(latest))]
        fresh = sorted((item for key, item in valid.items() if key not in self._seen), key=lambda item: item["id"])
        self._seen.update(valid)
        return [Decision(item["id"], decision_text(item)) for item in fresh]
