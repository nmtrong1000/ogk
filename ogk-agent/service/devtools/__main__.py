"""Usage (service running with OGK_DEV=1, same OGK_DATA_DIR):
python -m service.devtools inject [--vector NAME] [--child ID] [--count N]
python -m service.devtools offline DAYS
python -m service.devtools status
"""

import argparse
import json
import sys

import httpx

from service.core.ipc_server import IPC_FILE
from service.devtools import sample_events
from service.platform import get_platform


def _call(method: str, path: str, body: dict | None = None) -> int:
    ipc = json.loads((get_platform().data_dir() / IPC_FILE).read_text(encoding="utf-8"))
    response = httpx.request(
        method,
        f"http://127.0.0.1:{ipc['port']}{path}",
        json=body,
        headers={"Authorization": f"Bearer {ipc['token']}"},
        trust_env=False,
    )
    print(response.status_code, json.dumps(response.json(), ensure_ascii=False))
    return 0 if response.is_success else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m service.devtools")
    commands = parser.add_subparsers(dest="command", required=True)
    inject = commands.add_parser("inject", help="queue sample events from docs/test_vectors.json")
    inject.add_argument("--vector", default="app_start", choices=sorted(sample_events()))
    inject.add_argument("--child", type=int, default=None)
    inject.add_argument("--count", type=int, default=1)
    offline = commands.add_parser("offline", help="add simulated offline days")
    offline.add_argument("days", type=float)
    commands.add_parser("status", help="show service status")
    args = parser.parse_args(argv)
    if args.command == "inject":
        body = {"vector": args.vector, "count": args.count}
        if args.child is not None:
            body["child_id"] = args.child
        return _call("POST", "/ipc/dev/events", body)
    if args.command == "offline":
        return _call("POST", "/ipc/dev/offline", {"days": args.days})
    return _call("GET", "/ipc/status")


if __name__ == "__main__":
    sys.exit(main())
