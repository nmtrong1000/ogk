import tkinter as tk

from tray.features.requests.logic import Decision
from tray.ipc_client import IpcClient, IpcError


class RequestView:
    def __init__(self, root: tk.Tk, client: IpcClient, notify) -> None:
        self._root = root
        self._client = client
        self._notify = notify
        self._window: tk.Toplevel | None = None
        self._status: tk.Label | None = None

    def show(self) -> None:
        if self._window is None or not self._window.winfo_exists():
            self._window = tk.Toplevel(self._root)
            self._window.title("OGK - Gửi yêu cầu")
            self._window.attributes("-topmost", True)
            self._window.resizable(False, False)
            self._status = tk.Label(self._window, text="Con có thể nhờ bố mẹ xem xét.", padx=22, pady=16)
            self._status.pack()
            tk.Button(self._window, text="Xin thêm giờ", command=lambda: self._send({"type": "add_time"})).pack(
                fill="x", padx=18, pady=5
            )
            tk.Button(self._window, text="Đóng", command=self._window.destroy).pack(fill="x", padx=18, pady=(5, 16))
        self._window.deiconify()
        self._window.lift()

    def report_blocked(self, domain: str) -> None:
        self._send({"type": "blocked_domain", "domain": domain})

    def show_decision(self, decision: Decision) -> None:
        self._notify("OGK - Phản hồi của phụ huynh", decision.text)

    def _send(self, body: dict) -> None:
        try:
            self._client.create_request(body)
        except IpcError:
            self._notify("OGK", "Chưa gửi được yêu cầu. Con hãy thử lại sau.")
            return
        if self._status is not None and self._status.winfo_exists():
            self._status.config(text="Đã gửi. Bố mẹ sẽ phản hồi tại đây.")
        self._notify("OGK", "Đã gửi yêu cầu cho bố mẹ.")
