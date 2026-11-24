"""IpcError.code is the contract with the UI, which maps it to user-facing text; the message is English for logs.
A route may name error codes it passes through from the service body; any other failure stays bad_status.
"""

import json
import os
from pathlib import Path
from typing import Any

import httpx

IPC_FILE = "ipc.json"


class IpcError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IpcClient:
    def __init__(self, data_dir: Path, timeout: float = 3.0) -> None:
        self._file = data_dir / IPC_FILE
        self._timeout = timeout

    def _endpoint(self) -> tuple[int, str]:
        try:
            info = json.loads(self._file.read_text(encoding="utf-8"))
            return int(info["port"]), str(info["token"])
        except FileNotFoundError:
            raise IpcError("not_running", "Service is not running (IPC file not found)") from None
        except (OSError, ValueError, KeyError, TypeError):
            raise IpcError("bad_ipc_file", f"Invalid IPC file: {self._file}") from None

    def _request(self, method: str, path: str, body: Any = None, passthrough: frozenset[str] = frozenset()) -> Any:
        port, token = self._endpoint()
        try:
            response = httpx.request(
                method,
                f"http://127.0.0.1:{port}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise IpcError("unreachable", f"Cannot connect to service: {exc or type(exc).__name__}") from None
        if response.status_code == 401:
            raise IpcError("unauthorized", "Service rejected the token")
        if response.status_code != 200:
            code = _error_code(response)
            if code in passthrough:
                raise IpcError(code, f"Service refused: {code}")
            raise IpcError("bad_status", f"Service returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise IpcError("bad_response", "Service returned invalid data") from None

    def status(self) -> dict[str, Any]:
        return self._request("GET", "/ipc/status")

    def heartbeat(self, idle_seconds: float | None = None, foreground: str | None = None) -> None:
        body: dict[str, Any] = {"pid": os.getpid()}
        if idle_seconds is not None:
            body["idle_seconds"] = round(idle_seconds, 1)
        if foreground is not None:
            body["foreground"] = foreground
        self._request("POST", "/ipc/heartbeat", body)

    def screentime(self) -> dict[str, Any]:
        return self._request("GET", "/ipc/screentime")

    def appcontrol(self) -> dict[str, Any]:
        return self._request("GET", "/ipc/appcontrol")

    def webfilter(self) -> dict[str, Any]:
        return self._request("GET", "/ipc/webfilter")

    def requests(self) -> dict[str, Any]:
        return self._request("GET", "/ipc/requests")

    def create_request(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/ipc/requests", body)

    def child_view_link(self) -> dict[str, Any]:
        return self._request("POST", "/ipc/child-view", passthrough=CHILD_VIEW_ERRORS)


CHILD_VIEW_ERRORS = frozenset({"no_child", "child_view_failed", "not_available"})


def _error_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    code = body.get("error") if isinstance(body, dict) else None
    return code if isinstance(code, str) else None
