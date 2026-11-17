import sys

from service.core.agent import run_agent
from service.platform import get_platform


def main(argv: list[str] | None = None) -> None:
    get_platform().run_service(sys.argv if argv is None else argv, run_agent)
