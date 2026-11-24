"""The link is fetched off the Tk thread because the IPC call can block for its full timeout, and the service
contacts the server before answering. The URL is never logged or shown: its fragment is a live code.
"""

import threading
from collections.abc import Callable

from tray.features.reports.logic import TITLE, failure_text
from tray.ipc_client import IpcClient, IpcError

Notify = Callable[[str, str], None]


def fetch_and_open(client: IpcClient, open_url: Callable[[str], bool], notify: Notify) -> bool:
    try:
        link = client.child_view_link()
    except IpcError as exc:
        notify(TITLE, failure_text(exc.code))
        return False
    url = link.get("url") if isinstance(link, dict) else None
    if not isinstance(url, str) or not url.startswith("https://"):
        notify(TITLE, failure_text("bad_response"))
        return False
    try:
        opened = open_url(url)
    except Exception:
        opened = False
    if not opened:
        notify(TITLE, failure_text("browser_failed"))
    return opened


def open_child_view(client: IpcClient, open_url: Callable[[str], bool], notify: Notify) -> None:
    threading.Thread(
        target=fetch_and_open, args=(client, open_url, notify), name="child-view-link", daemon=True
    ).start()
