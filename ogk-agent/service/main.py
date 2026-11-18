"""'enroll' is handled before run_service because on Windows any extra argument is passed to pywin32's
HandleCommandLine, which would reject it as an unknown service command.
"""

import sys

from service.core.agent import run_agent
from service.platform import get_platform

ENROLL_COMMAND = "enroll"


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv if argv is None else argv
    platform = get_platform()
    if len(argv) > 1 and argv[1] == ENROLL_COMMAND:
        from service.modules.enrollment.command import main as enroll_main

        sys.exit(enroll_main(argv[2:], platform.data_dir()))
    platform.run_service(argv, run_agent)
