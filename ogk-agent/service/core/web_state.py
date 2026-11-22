import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebState:
    block_seq: int = 0
    domain: str | None = None
    reason: str = ""
    set_by: str = ""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def blocked(self, domain: str, reason: str, set_by: str) -> None:
        with self.lock:
            self.domain, self.reason, self.set_by = domain, reason, set_by
            self.block_seq += 1

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "block_seq": self.block_seq,
                "domain": self.domain,
                "reason": self.reason,
                "set_by": self.set_by,
                "run_id": self.run_id,
            }
