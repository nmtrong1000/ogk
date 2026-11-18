"""The health check carries no secret, but once the device is enrolled it still uses the pinned certificate
so a changed server certificate shows up as unreachable instead of healthy.
The device check logs only when its outcome changes, so a long outage or revocation does not flood the log.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from service.core.config import Config, load_config
from service.core.device_session import DeviceRevoked, DeviceSession, NotEnrolled
from service.core.ipc_server import IpcServer
from service.core.local_db import LocalDb
from service.core.server_client import ApiError, CertificatePinError, ServerClient

log = logging.getLogger("ogk.agent")


class Agent:
    def __init__(
        self, config: Config, client: ServerClient, data_dir: Path, session: DeviceSession | None = None
    ) -> None:
        self._config = config
        self._client = client
        self._session = session
        self._device_outcome: str | None = None
        self._ipc = IpcServer(data_dir, config.ipc_port, self.status)
        self._started = time.monotonic()
        self._server_reachable: bool | None = None

    def status(self) -> dict[str, Any]:
        return {
            "uptime": round(time.monotonic() - self._started, 1),
            "server_reachable": self._server_reachable,
            "enrollment": None if self._session is None else self._session.state,
        }

    async def run(self, stop_event: asyncio.Event) -> None:
        log.info("agent started, server %s", self._config.server_url)
        self._started = time.monotonic()
        tasks: list[asyncio.Task] = []
        stop_task = asyncio.create_task(stop_event.wait(), name="stop")
        try:
            await self._ipc.start()
            tasks.append(asyncio.create_task(self._health_loop(), name="health"))
            if self._session is not None:
                tasks.append(asyncio.create_task(self._device_loop(), name="device"))
            await asyncio.wait([stop_task, *tasks], return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in [stop_task, *tasks]:
                task.cancel()
            await asyncio.gather(stop_task, *tasks, return_exceptions=True)
            await self._ipc.stop()
            await self._client.aclose()
            if self._session is not None:
                await self._session.aclose()
        for task in tasks:
            if not task.cancelled() and task.exception() is not None:
                raise task.exception()
        log.info("agent stopped")

    async def check_health(self) -> bool:
        try:
            body = await self._client.health()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("server unreachable: %s", exc or type(exc).__name__)
            self._server_reachable = False
            return False
        log.info("server ok: %s", body)
        self._server_reachable = True
        return True

    def _device_log(self, outcome: str, level: int, message: str, *args: Any) -> None:
        if outcome != self._device_outcome:
            log.log(level, message, *args)
        self._device_outcome = outcome

    async def check_device(self) -> bool:
        try:
            info = await self._session.me()
        except NotEnrolled:
            self._device_log(
                "not_enrolled", logging.WARNING, "device not enrolled; run 'ogk_service enroll' as Administrator"
            )
            return False
        except DeviceRevoked:
            self._device_log("revoked", logging.ERROR, "device is revoked; API calls stopped")
            return False
        except CertificatePinError as exc:
            self._device_log("pin", logging.ERROR, "refusing to connect: %s", exc)
            return False
        except (httpx.HTTPError, ApiError) as exc:
            self._device_log("error", logging.WARNING, "device check failed: %s", exc or type(exc).__name__)
            return False
        self._device_log("ok", logging.INFO, "device %s authenticated as %s", info["id"], info["name"])
        return True

    async def _device_loop(self) -> None:
        while True:
            await self.check_device()
            await asyncio.sleep(self._config.health_interval)

    async def _health_loop(self) -> None:
        while True:
            await self.check_health()
            await asyncio.sleep(self._config.health_interval)


async def run_agent(data_dir: Path, stop_event: asyncio.Event) -> None:
    config = load_config(data_dir)
    db = LocalDb(data_dir)
    creds = await asyncio.to_thread(db.load)
    pin = creds.cert_sha256 if creds is not None and creds.server_url == config.server_url else None
    client = ServerClient(config.server_url, config.ca_cert, pin_sha256=pin)
    await Agent(config, client, data_dir, DeviceSession(config, db)).run(stop_event)
