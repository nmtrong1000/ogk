import asyncio
import logging
from pathlib import Path

import httpx

from service.core.config import Config, load_config
from service.core.server_client import ServerClient

log = logging.getLogger("ogk.agent")


class Agent:
    def __init__(self, config: Config, client: ServerClient) -> None:
        self._config = config
        self._client = client

    async def run(self, stop_event: asyncio.Event) -> None:
        log.info("agent started, server %s", self._config.server_url)
        tasks = [asyncio.create_task(self._health_loop(), name="health")]
        stop_task = asyncio.create_task(stop_event.wait(), name="stop")
        try:
            await asyncio.wait([stop_task, *tasks], return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in [stop_task, *tasks]:
                task.cancel()
            await asyncio.gather(stop_task, *tasks, return_exceptions=True)
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
            return False
        log.info("server ok: %s", body)
        return True

    async def _health_loop(self) -> None:
        while True:
            await self.check_health()
            await asyncio.sleep(self._config.health_interval)


async def run_agent(data_dir: Path, stop_event: asyncio.Event) -> None:
    config = load_config(data_dir)
    client = ServerClient(config.server_url, config.ca_cert)
    await Agent(config, client).run(stop_event)
