import json
from pathlib import Path
from typing import Any

import httpx

IPC_FILE = "ipc.json"


class IpcError(Exception):
    pass


class IpcClient:
    def __init__(self, data_dir: Path, timeout: float = 3.0) -> None:
        self._file = data_dir / IPC_FILE
        self._timeout = timeout

    def _endpoint(self) -> tuple[int, str]:
        try:
            info = json.loads(self._file.read_text(encoding="utf-8"))
            return int(info["port"]), str(info["token"])
        except FileNotFoundError:
            raise IpcError("Service chưa chạy (không thấy tệp kết nối)") from None
        except (OSError, ValueError, KeyError, TypeError):
            raise IpcError(f"Tệp kết nối không hợp lệ: {self._file}") from None

    def _get(self, path: str) -> Any:
        port, token = self._endpoint()
        try:
            response = httpx.get(
                f"http://127.0.0.1:{port}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise IpcError(f"Không kết nối được service: {exc or type(exc).__name__}") from None
        if response.status_code == 401:
            raise IpcError("Service từ chối token")
        if response.status_code != 200:
            raise IpcError(f"Service trả lỗi {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise IpcError("Service trả dữ liệu không hợp lệ") from None

    def status(self) -> dict[str, Any]:
        return self._get("/ipc/status")
