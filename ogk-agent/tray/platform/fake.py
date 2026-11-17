import os
import tkinter as tk
from pathlib import Path

import pystray


def data_dir() -> Path:
    return Path(os.environ.get("OGK_DATA_DIR", ".ogk-data")).resolve()


def run_tray(icon: pystray.Icon, root: tk.Tk) -> None:
    # macOS: pystray và Tk cùng cần main thread, pystray dùng chung run loop của Tk.
    icon.run_detached()
    root.mainloop()
