"""All methods run on the Tk thread. The lock notice stays up for LOCK_DELAY_MS so the reason is read before
the screen locks; it is short because the service expects the lock within 5 seconds of its order. Lock orders
arriving while a notice is open are dropped: the pending lock already covers them.
"""

import logging
import tkinter as tk
from collections.abc import Callable

from tray.features.screentime.logic import REMAINING_TITLE, LockOrder, Plan

log = logging.getLogger("ogk.tray")

LOCK_DELAY_MS = 2000


def _topmost(root: tk.Tk, title: str) -> tuple[tk.Toplevel, tk.Label]:
    window = tk.Toplevel(root)
    window.title(title)
    window.attributes("-topmost", True)
    window.resizable(False, False)
    label = tk.Label(window, justify="left", padx=24, pady=20, font=("TkDefaultFont", 13))
    label.pack()
    return window, label


class ScreenTimeView:
    def __init__(self, root: tk.Tk, lock: Callable[[], bool], notify: Callable[[str, str], None]) -> None:
        self._root = root
        self._lock = lock
        self._notify = notify
        self._remaining: tuple[tk.Toplevel, tk.Label] | None = None
        self._grace: tuple[tk.Toplevel, tk.Label] | None = None
        self._notice: tuple[tk.Toplevel, tk.Label] | None = None
        self._lock_order: LockOrder | None = None
        self.remaining = "Đang hỏi service..."

    def show_remaining(self) -> None:
        if self._remaining is None or not self._remaining[0].winfo_exists():
            window = tk.Toplevel(self._root)
            window.title(REMAINING_TITLE)
            label = tk.Label(window, padx=24, pady=20, font=("TkDefaultFont", 16))
            label.pack()
            self._remaining = (window, label)
        self._remaining[0].deiconify()
        self._remaining[0].lift()
        self._remaining[1].config(text=self.remaining)

    def apply(self, plan: Plan) -> None:
        self.remaining = plan.remaining
        if self._remaining is not None and self._remaining[0].winfo_exists():
            self._remaining[1].config(text=plan.remaining)
        if plan.notify is not None:
            self._notify(*plan.notify)
        self._show_grace(plan.grace)
        if plan.lock is not None:
            self._start_lock(plan.lock)

    def _show_grace(self, text: str | None) -> None:
        if text is None:
            if self._grace is not None and self._grace[0].winfo_exists():
                self._grace[0].destroy()
            self._grace = None
            return
        if self._grace is None or not self._grace[0].winfo_exists():
            self._grace = _topmost(self._root, "OGK - Sắp khóa máy")
        self._grace[1].config(text=text)

    def _start_lock(self, order: LockOrder) -> None:
        if self._notice is not None and self._notice[0].winfo_exists():
            return
        self._lock_order = order
        log.info("received workstation lock order seq=%s", order.seq)
        try:
            self._show_grace(None)
            self._notice = _topmost(self._root, "OGK - Khóa máy")
            self._notice[1].config(text=order.text)
        except Exception:
            log.exception("failed to show workstation lock notice seq=%s", order.seq)
        finally:
            self._root.after(LOCK_DELAY_MS, self._finish_lock)

    def _finish_lock(self) -> None:
        order = self._lock_order
        log.info("calling LockWorkStation for seq=%s", None if order is None else order.seq)
        try:
            locked = self._lock()
        except Exception:
            log.exception("LockWorkStation raised an exception")
            locked = False
        if locked:
            log.info("LockWorkStation accepted seq=%s", None if order is None else order.seq)
        else:
            log.error("LockWorkStation failed seq=%s", None if order is None else order.seq)
            self._notify("OGK - Không khóa được máy", "Windows chưa khóa được phiên. OGK sẽ thử lại.")
        if self._notice is not None and self._notice[0].winfo_exists():
            self._notice[0].destroy()
        self._notice = None
        self._lock_order = None
