import threading
from typing import Any


class RequestState:
    def __init__(self) -> None:
        self._items: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def update(self, items: list[dict[str, Any]]) -> None:
        with self._lock:
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("id"), int):
                    self._items[item["id"]] = item
            self._items = dict(sorted(self._items.items())[-20:])

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"results": list(self._items.values())}
