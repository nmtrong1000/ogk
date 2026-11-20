"""Polls on its own thread and hands each notice to the Tk thread through post, so Tk is never touched here."""

import threading
from collections.abc import Callable

from tray.features.appcontrol.logic import BlockNotice, BlockTracker
from tray.ipc_client import IpcClient, IpcError

POLL_SECONDS = 1.0


def poll_once(client: IpcClient, tracker: BlockTracker) -> BlockNotice | None:
    try:
        snapshot = client.appcontrol()
    except IpcError:
        return None
    return tracker.update(snapshot)


def poll_loop(
    client: IpcClient, show: Callable[[BlockNotice], None], stop: threading.Event, interval: float = POLL_SECONDS
) -> None:
    tracker = BlockTracker()
    while not stop.is_set():
        notice = poll_once(client, tracker)
        if notice is not None:
            show(notice)
        stop.wait(interval)


def start_polling(
    client: IpcClient, post: Callable[[Callable[[], None]], None], show: Callable[[BlockNotice], None]
) -> threading.Event:
    stop = threading.Event()

    def hand_over(notice: BlockNotice) -> None:
        post(lambda: show(notice))

    threading.Thread(target=poll_loop, args=(client, hand_over, stop), name="appcontrol", daemon=True).start()
    return stop
