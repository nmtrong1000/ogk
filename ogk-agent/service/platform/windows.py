import asyncio
import logging
import os
from pathlib import Path

import servicemanager
import win32service
import win32serviceutil

from service.core.logging_setup import setup_logging
from service.platform import Entry

log = logging.getLogger("ogk.platform")

SERVICE_NAME = "OGKAgent"

_entry: Entry | None = None


def data_dir() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "OGK"


class OGKService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = "OGK Agent Service"
    _svc_description_ = "OGK: hỗ trợ quản lý việc sử dụng máy tính của trẻ em"

    def __init__(self, args) -> None:
        super().__init__(args)
        self._loop = asyncio.new_event_loop()
        self._stop_event = asyncio.Event()

    def SvcStop(self) -> None:
        log.info("stop requested by SCM")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._loop.call_soon_threadsafe(self._stop_event.set)

    def SvcDoRun(self) -> None:
        directory = data_dir()
        setup_logging(directory)
        log.info("service started, data dir %s", directory)
        try:
            self._loop.run_until_complete(_entry(directory, self._stop_event))
        except Exception:
            log.exception("service crashed")
            logging.shutdown()
            os._exit(1)
        finally:
            self._loop.close()
        log.info("service stopped")


def run_service(argv: list[str], entry: Entry) -> None:
    global _entry
    _entry = entry
    if len(argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(OGKService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(OGKService, argv=argv)
