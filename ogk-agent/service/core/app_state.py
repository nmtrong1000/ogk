"""The app-control module writes this state and the IPC route hands a snapshot to the Tray UI.
block_seq only grows within one service run: the Tray UI shows one explanation per new value and treats its
first poll as the baseline, so a restarted Tray UI does not replay an old block. block_seq is in memory and
starts again at 0 when the service restarts, while a running Tray UI may outlive that restart; run_id changes
with every service run so the Tray UI resets its baseline instead of silencing blocks it took for old ones.
"""

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AppState:
    block_seq: int = 0
    app: str | None = None
    set_by: str = ""
    source: str = ""
    reason: str = "app_rule"
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def blocked(self, app: str, set_by: str, source: str, reason: str = "app_rule") -> None:
        self.app, self.set_by, self.source, self.reason = app, set_by, source, reason
        self.block_seq += 1

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)
