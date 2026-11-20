"""All methods run on the Tk thread. A new block while the window is open replaces its text instead of stacking
windows, since a child relaunching a blocked game would otherwise bury the screen.
"""

import tkinter as tk

from tray.features.appcontrol.logic import TITLE, BlockNotice


class BlockView:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._window: tk.Toplevel | None = None
        self._label: tk.Label | None = None

    def show(self, notice: BlockNotice) -> None:
        if self._window is None or not self._window.winfo_exists():
            self._window = tk.Toplevel(self._root)
            self._window.title(TITLE)
            self._window.attributes("-topmost", True)
            self._window.resizable(False, False)
            self._label = tk.Label(self._window, justify="left", padx=24, pady=20, font=("TkDefaultFont", 13))
            self._label.pack()
            tk.Button(self._window, text="Đã hiểu", command=self._window.destroy).pack(pady=(0, 16))
        self._label.config(text=notice.text)
        self._window.deiconify()
        self._window.lift()
