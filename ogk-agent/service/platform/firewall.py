from pathlib import Path

from service.platform import get_platform


def configure(directory: Path) -> None:
    get_platform().configure_firewall(directory)


def restore(directory: Path) -> None:
    get_platform().restore_firewall(directory)
