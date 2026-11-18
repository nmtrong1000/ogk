"""There is deliberately no Quit item: the agent has no hidden mode, and the service would relaunch the
Tray UI anyway.
"""

from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw


def _image() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), fill=(34, 139, 84, 255))
    draw.ellipse((20, 20, 44, 44), fill=(255, 255, 255, 255))
    return image


TOOLTIP = "OGK đang chạy: máy tính này được phụ huynh quản lý"


def create_icon(on_open: Callable[[], None]) -> pystray.Icon:
    menu = pystray.Menu(pystray.MenuItem("Mở OGK", lambda: on_open(), default=True))
    return pystray.Icon("ogk-tray", _image(), TOOLTIP, menu=menu)
