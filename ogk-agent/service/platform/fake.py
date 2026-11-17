import asyncio
import logging
import os
import signal
from pathlib import Path

from service.core.logging_setup import setup_logging
from service.platform import Entry

log = logging.getLogger("ogk.platform")


def data_dir() -> Path:
    return Path(os.environ.get("OGK_DATA_DIR", ".ogk-data")).resolve()


def run_service(argv: list[str], entry: Entry) -> None:
    directory = data_dir()
    setup_logging(directory, console=True)
    log.info("fake platform, data dir %s", directory)

    async def _main() -> None:
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await entry(directory, stop_event)

    asyncio.run(_main())
