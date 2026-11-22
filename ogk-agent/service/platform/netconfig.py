from pathlib import Path

from service.platform import get_platform


def configure_dns(directory: Path) -> None:
    get_platform().configure_dns(directory)


def restore_dns(directory: Path) -> None:
    get_platform().restore_dns(directory)


def disable_doh(directory: Path) -> None:
    get_platform().disable_doh(directory)


def restore_doh(directory: Path) -> None:
    get_platform().restore_doh(directory)
