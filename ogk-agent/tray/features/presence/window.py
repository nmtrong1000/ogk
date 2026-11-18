import threading
import tkinter as tk
from collections.abc import Callable
from typing import Any

from tray.ipc_client import IpcClient, IpcError


ERROR_TEXT = {
    "not_running": "Service chưa chạy",
    "bad_ipc_file": "Tệp kết nối của service bị hỏng",
    "unreachable": "Không kết nối được service",
    "unauthorized": "Service từ chối kết nối",
    "bad_status": "Service đang gặp lỗi",
    "bad_response": "Service đang gặp lỗi",
}


def describe_error(exc: IpcError) -> str:
    return ERROR_TEXT.get(exc.code, "Có lỗi khi hỏi service")


def describe(status: dict[str, Any]) -> str:
    server = {True: "kết nối được", False: "không kết nối được", None: "chưa kiểm tra"}
    return (
        f"Service: đang chạy ({status.get('uptime', 0):.0f} giây)\n"
        f"Server: {server.get(status.get('server_reachable'), 'không rõ')}"
    )


class StatusWindow:
    def __init__(self, root: tk.Tk, client: IpcClient, post: Callable[[Callable[[], None]], None]) -> None:
        self._root = root
        self._client = client
        self._post = post
        self._window: tk.Toplevel | None = None
        self._label: tk.Label | None = None

    def show(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.deiconify()
            self._window.lift()
        else:
            self._window = tk.Toplevel(self._root)
            self._window.title("OGK")
            self._window.geometry("360x160")
            self._label = tk.Label(self._window, justify="left", padx=20, pady=20)
            self._label.pack(anchor="w")
            tk.Button(self._window, text="Làm mới", command=self.refresh).pack()
        self.refresh()

    def refresh(self) -> None:
        if self._label is not None:
            self._label.config(text="Đang hỏi service...")
        threading.Thread(target=self._fetch, name="ipc-status", daemon=True).start()

    def _fetch(self) -> None:
        try:
            text = describe(self._client.status())
        except IpcError as exc:
            text = describe_error(exc)
        self._post(lambda: self._set_text(text))

    def _set_text(self, text: str) -> None:
        if self._window is not None and self._window.winfo_exists() and self._label is not None:
            self._label.config(text=text)
