import asyncio
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import ModuleType

Entry = Callable[[Path, asyncio.Event], Awaitable[None]]


def get_platform() -> ModuleType:
    if sys.platform == "win32":
        from service.platform import windows

        return windows
    from service.platform import fake

    return fake
