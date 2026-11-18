"""A Tray UI this service launched counts as alive while its process runs; one it did not launch (left over
from a previous service run) counts as alive while its heartbeats are fresh. The startup grace gives such a
leftover Tray UI one heartbeat period to show up before a second copy is launched.
Logoff is not a failure: the Tray UI is expected to die with the session. Heartbeats with no active
session come from a Tray UI that is shutting down, so they are ignored.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from types import ModuleType

from service.core.agent import ModuleContext
from service.core.bus import SESSION, TRAY_HEARTBEAT, Bus, SessionEvent
from service.core.enforcement import Enforcement

log = logging.getLogger("ogk.presence")

TRAY_UNAVAILABLE = "tray_unavailable"


class PresenceMonitor:
    def __init__(
        self,
        bus: Bus,
        enforcement: Enforcement,
        platform: ModuleType,
        *,
        check_interval: float = 1.0,
        startup_grace: float = 6.0,
        heartbeat_timeout: float = 15.0,
        start_timeout: float = 15.0,
        max_failures: int = 3,
        retry_interval: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._enforcement = enforcement
        self._platform = platform
        self._check_interval = check_interval
        self._startup_grace = startup_grace
        self._heartbeat_timeout = heartbeat_timeout
        self._start_timeout = start_timeout
        self._max_failures = max_failures
        self._retry_interval = retry_interval
        self._clock = clock
        self._session: int | None = None
        self._process = None
        self._process_session: int | None = None
        self._launched_at: float | None = None
        self._last_heartbeat: float | None = None
        self._failures = 0
        self._next_attempt = 0.0
        bus.subscribe(SESSION, self._on_session)
        bus.subscribe(TRAY_HEARTBEAT, self._on_heartbeat)

    @property
    def failures(self) -> int:
        return self._failures

    def _on_session(self, event: SessionEvent) -> None:
        log.info("session %s, id %d", event.kind, event.session_id)
        if event.kind in ("logon", "unlock"):
            self._session = event.session_id
        elif event.kind == "logoff" and event.session_id == self._session:
            self._session = None
            self._last_heartbeat = None

    def _on_heartbeat(self, pid: int) -> None:
        if self._session is None:
            return
        self._last_heartbeat = self._clock()
        if self._launched_at is not None:
            log.info("tray ui is up (pid %d)", pid)
            self._launched_at = None
        self._failures = 0
        self._enforcement.enable()

    async def run(self) -> None:
        info = await asyncio.to_thread(self._platform.current_session)
        if info is not None and self._session is None:
            self._session = info.session_id
            log.info("active session %d (%s)", info.session_id, info.username)
        self._next_attempt = self._clock() + self._startup_grace
        try:
            while True:
                await self.tick()
                await asyncio.sleep(self._check_interval)
        finally:
            if self._process is not None:
                self._process.terminate()
                log.info("tray ui stopped with the service")

    async def tick(self) -> None:
        now = self._clock()
        if self._process is not None and self._process_session != self._session:
            log.info("tray ui (pid %d) stopped: session %s ended", self._process.pid, self._process_session)
            await self._stop_process()
            self._launched_at = None
        if self._session is None:
            return
        if self._launched_at is not None:
            if self._process.alive() and now - self._launched_at < self._start_timeout:
                return
            reason = (
                "exited before its first heartbeat"
                if not self._process.alive()
                else f"no heartbeat within {self._start_timeout:g}s"
            )
            await self._stop_process()
            self._fail(now, reason)
        if self._tray_alive(now) or now < self._next_attempt:
            return
        if self._process is not None:
            log.warning("tray ui (pid %d) exited, launching again", self._process.pid)
            self._process = None
        await self._launch()

    def _tray_alive(self, now: float) -> bool:
        if self._process is not None:
            return self._process.alive()
        return self._last_heartbeat is not None and now - self._last_heartbeat < self._heartbeat_timeout

    async def _launch(self) -> None:
        session = self._session
        try:
            process = await asyncio.to_thread(self._platform.launch_tray, session)
        except Exception as exc:
            self._fail(self._clock(), f"launch error: {exc}")
            return
        self._process = process
        self._process_session = session
        self._launched_at = self._clock()
        self._last_heartbeat = None
        log.info("tray ui launched (pid %d) in session %d", process.pid, session)

    async def _stop_process(self) -> None:
        process, self._process = self._process, None
        self._last_heartbeat = None
        if process is not None:
            await asyncio.to_thread(process.terminate)

    def _fail(self, now: float, reason: str) -> None:
        self._failures += 1
        self._launched_at = None
        log.warning("tray ui start failed (%d/%d): %s", self._failures, self._max_failures, reason)
        if self._failures >= self._max_failures:
            self._enforcement.disable(TRAY_UNAVAILABLE)
            self._next_attempt = now + self._retry_interval


def create(context: ModuleContext) -> PresenceMonitor:
    return PresenceMonitor(context.bus, context.enforcement, context.platform)
