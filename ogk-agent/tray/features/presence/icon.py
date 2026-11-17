from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw


def _image() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), fill=(34, 139, 84, 255))
    draw.ellipse((20, 20, 44, 44), fill=(255, 255, 255, 255))
    return image


def create_icon(on_open: Callable[[], None], on_quit: Callable[[], None]) -> pystray.Icon:
    menu = pystray.Menu(
        pystray.MenuItem("Mở OGK", lambda: on_open(), default=True),
        pystray.MenuItem("Thoát", lambda: on_quit()),
    )
    return pystray.Icon("ogk-tray", _image(), "OGK", menu=menu)
