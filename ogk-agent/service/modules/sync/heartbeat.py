"""Every tick sends queued events first, then the heartbeat. Any failed heartbeat counts as offline time, so
an unreachable server, a revoked device or a pinning failure all lead to the default policy after the limit.
quota_used is today's counted seconds per child from the screen-time state; device alerts are the
enforcement alert plus whatever the AlertBoard holds.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

import aiohttp
import httpx

from service.core.agent import ModuleContext
from service.core.alerts import AlertBoard
from service.core.bus import POLICY_STALE, SERVER_TIME, Bus
from service.core.commands import CommandState
from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.enforcement import Enforcement
from service.core.event_queue import EventQueue
from service.core.events import format_ts
from service.core.offline import OfflineGuard
from service.core.policy_store import PolicyStore
from service.core.screen_state import ScreenState
from service.core.server_client import ApiError

log = logging.getLogger("ogk.sync")

ALERT_ENFORCEMENT_DISABLED = "enforcement_disabled"


def parse_server_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("server_time missing")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class SyncModule:
    def __init__(
        self,
        session: DeviceSession | None,
        queue: EventQueue,
        offline: OfflineGuard,
        store: PolicyStore,
        enforcement: Enforcement,
        bus: Bus,
        interval: float,
        screen: ScreenState | None = None,
        alerts: AlertBoard | None = None,
        commands: CommandState | None = None,
    ) -> None:
        self._screen = screen
        self._alerts = alerts
        self._commands = commands
        self._session = session
        self._queue = queue
        self._offline = offline
        self._store = store
        self._enforcement = enforcement
        self._bus = bus
        self._interval = interval
        self._started = time.monotonic()
        self._last_error: str | None = None

    def body(self) -> dict[str, Any]:
        versions = self._store.versions()
        snapshot = self._enforcement.snapshot()
        alerts = []
        if not snapshot["enabled"]:
            alerts.append(
                {
                    "type": ALERT_ENFORCEMENT_DISABLED,
                    "detail": snapshot["reason"],
                    "ts": snapshot["since"] or format_ts(datetime.now(UTC)),
                }
            )
        if self._alerts is not None:
            alerts.extend(
                {"type": alert.type, "detail": alert.detail, "ts": format_ts(alert.since)}
                for alert in self._alerts.active()
            )
        used = {} if self._screen is None else self._screen.used_today
        return {
            "status": {
                "uptime": round(time.monotonic() - self._started, 1),
                "enforcement": snapshot,
                "policy_mode": self._store.mode,
            },
            "quota_used": {str(child_id): used.get(child_id, 0) for child_id in versions},
            "policy_versions": {str(child_id): version for child_id, version in versions.items()},
            "alerts": alerts,
        }

    def _stale(self, server_versions: dict[str, int]) -> bool:
        local = self._store.versions()
        remote = {int(child_id): version for child_id, version in server_versions.items()}
        return set(remote) != set(local) or any(version > local[child_id] for child_id, version in remote.items())

    def _log_failure(self, message: str) -> None:
        if message != self._last_error:
            log.warning("heartbeat failed, counting offline time: %s", message)
        self._last_error = message

    async def tick(self) -> bool:
        if self._session is None:
            return False
        await self._queue.flush()
        try:
            response = await self._session.heartbeat(self.body())
            server_time = parse_server_time(response.get("server_time"))
            versions = response.get("policy_versions") or {}
        except (NotEnrolled, DeviceRevoked, httpx.HTTPError, ApiError, ValueError, AttributeError) as exc:
            self._log_failure(str(exc) or type(exc).__name__)
            self._bus.publish(SERVER_TIME, None)
            await asyncio.to_thread(self._offline.offline)
            return False
        if self._last_error is not None:
            log.info("heartbeat ok again")
        self._last_error = None
        await asyncio.to_thread(self._offline.online, server_time)
        self._bus.publish(SERVER_TIME, server_time)
        if self._stale(versions):
            log.info("server has newer policies %s, local %s; downloading", versions, self._store.versions())
            self._bus.publish(POLICY_STALE)
        if self._commands is not None:
            for command in response.get("commands", []):
                if await self._commands.process(command):
                    try:
                        await self._session.acknowledge_command(command["id"])
                    except (NotEnrolled, DeviceRevoked, httpx.HTTPError, ApiError) as exc:
                        log.warning("command acknowledgement failed: %s", exc or type(exc).__name__)
        return True

    async def run(self) -> None:
        tasks = [asyncio.create_task(self._heartbeat_loop()), asyncio.create_task(self._websocket_loop())]
        await asyncio.gather(*tasks)

    async def _heartbeat_loop(self) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(self._interval)

    async def _websocket_loop(self) -> None:
        if self._session is None or self._commands is None:
            return
        while True:
            try:
                base_url, token, pin = await self._session.websocket_credentials()
                ws_url = base_url.replace("https://", "wss://", 1).rstrip("/") + "/api/device/ws"
                fingerprint = aiohttp.Fingerprint(bytes.fromhex(pin))
                async with (
                    aiohttp.ClientSession() as client,
                    client.ws_connect(
                        ws_url,
                        headers={"Authorization": f"Bearer {token}"},
                        ssl=fingerprint,
                        heartbeat=20,
                        receive_timeout=45,
                    ) as socket,
                ):
                    log.info("command websocket connected")
                    async for message in socket:
                        if message.type != aiohttp.WSMsgType.TEXT:
                            continue
                        try:
                            envelope = message.json()
                            command = envelope["command"]
                        except (ValueError, KeyError, TypeError):
                            log.warning("ignored malformed websocket command")
                            continue
                        if await self._commands.process(command):
                            await socket.send_json({"type": "ack", "id": command["id"]})
            except asyncio.CancelledError:
                raise
            except (TimeoutError, aiohttp.ClientError, NotEnrolled, DeviceRevoked, ApiError, ValueError) as exc:
                log.warning("command websocket disconnected: %s", exc or type(exc).__name__)
                await asyncio.sleep(1)


def create(context: ModuleContext) -> SyncModule:
    return SyncModule(
        context.session,
        context.event_queue,
        context.offline,
        context.policy_store,
        context.enforcement,
        context.bus,
        context.config.heartbeat_interval,
        context.screen,
        context.alerts,
        context.commands,
    )
