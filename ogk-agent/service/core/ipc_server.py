import hmac
import json
import logging
import os
import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiohttp import web

log = logging.getLogger("ogk.ipc")

IPC_HOST = "127.0.0.1"
IPC_FILE = "ipc.json"

StatusProvider = Callable[[], dict[str, Any]]


class IpcServer:
    def __init__(self, data_dir: Path, port: int, status_provider: StatusProvider) -> None:
        self._file = data_dir / IPC_FILE
        self._port = port
        self._status = status_provider
        self._token = ""
        self._runner: web.AppRunner | None = None

    @property
    def port(self) -> int:
        return self._port

    async def start(self) -> None:
        self._token = secrets.token_urlsafe(32)
        app = web.Application(middlewares=[self._auth])
        app.router.add_get("/ipc/status", self._handle_status)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, IPC_HOST, self._port)
        await site.start()
        self._port = self._runner.addresses[0][1]
        self._write_file()
        log.info("ipc listening on %s:%d", IPC_HOST, self._port)

    async def stop(self) -> None:
        self._file.unlink(missing_ok=True)
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        log.info("ipc stopped")

    def _write_file(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_name(self._file.name + ".tmp")
        tmp.write_text(json.dumps({"port": self._port, "token": self._token}), encoding="utf-8")
        if os.name == "posix":
            os.chmod(tmp, 0o644)
        os.replace(tmp, self._file)

    @web.middleware
    async def _auth(self, request: web.Request, handler) -> web.StreamResponse:
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme != "Bearer" or not hmac.compare_digest(token.encode(), self._token.encode()):
            return web.json_response({"error": "unauthorized"}, status=401)
        return await handler(request)

    async def _handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", **self._status()})
