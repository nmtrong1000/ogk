import sys
from types import ModuleType


def get_platform() -> ModuleType:
    if sys.platform == "win32":
        from tray.platform import windows

        return windows
    from tray.platform import fake

    return fake
