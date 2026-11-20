"""create_time is part of a process's identity: Windows reuses PIDs, so a kill re-checks it to never hit a
different process that took over the PID after the scan.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    create_time: float
    name: str
    exe: str
    session_id: int | None
