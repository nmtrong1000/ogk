"""'enroll' is handled before run_service because on Windows any extra argument is passed to pywin32's
HandleCommandLine, which would reject it as an unknown service command. 'fake-session' exists only on the
Mac fake platform.
"""

import sys
from functools import partial

from service.core.agent import run_agent
from service.modules import policy, presence, sync
from service.platform import get_platform

ENROLL_COMMAND = "enroll"
FAKE_SESSION_COMMAND = "fake-session"
MODULES = [presence.create, policy.create, sync.create]


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv if argv is None else argv
    platform = get_platform()
    if len(argv) > 1 and argv[1] == ENROLL_COMMAND:
        from service.modules.enrollment.command import main as enroll_main

        sys.exit(enroll_main(argv[2:], platform.data_dir()))
    if len(argv) > 1 and argv[1] == FAKE_SESSION_COMMAND and hasattr(platform, "session_command"):
        sys.exit(platform.session_command(argv[2:], platform.data_dir()))
    platform.run_service(argv, partial(run_agent, modules=MODULES))
