import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from service.core.config import Config, load_config
from service.core.ipc_server import IpcServer
from service.core.server_client import ServerClient

log = logging.getLogger("ogk.agent")


class Agent:
    def __init__(self, config: Config, client: ServerClient, data_dir: Path) -> None:
        self._config = config
        self._client = client
        self._ipc = IpcServer(data_dir, config.ipc_port, self.status)
        self._started = time.monotonic()
        self._server_reachable: bool | None = None

    def status(self) -> dict[str, Any]:
        return {
            "uptime": round(time.monotonic() - self._started, 1),
            "server_reachable": self._server_reachable,
        }

    async def run(self, stop_event: asyncio.Event) -> None:
        log.info("agent started, server %s", self._config.server_url)
        self._started = time.monotonic()
        tasks: list[asyncio.Task] = []
        stop_task = asyncio.create_task(stop_event.wait(), name="stop")
        try:
            await self._ipc.start()
            tasks.append(asyncio.create_task(self._health_loop(), name="health"))
            await asyncio.wait([stop_task, *tasks], return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in [stop_task, *tasks]:
                task.cancel()
            await asyncio.gather(stop_task, *tasks, return_exceptions=True)
            await self._ipc.stop()
            await self._client.aclose()
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

    async def _health_loop(self) -> None:
        while True:
            await self.check_health()
            await asyncio.sleep(self._config.health_interval)


async def run_agent(data_dir: Path, stop_event: asyncio.Event) -> None:
    config = load_config(data_dir)
    client = ServerClient(config.server_url, config.ca_cert)
    await Agent(config, client, data_dir).run(stop_event)
