import threading
from collections.abc import Callable

from tray.features.webfilter.logic import BlockNotice, BlockTracker
from tray.ipc_client import IpcClient, IpcError

POLL_SECONDS = 1.0


def poll_once(client: IpcClient, tracker: BlockTracker) -> BlockNotice | None:
    try:
        snapshot = client.webfilter()
    except IpcError:
        return None
    return tracker.update(snapshot)


def poll_loop(client: IpcClient, show: Callable[[BlockNotice], None], stop: threading.Event) -> None:
    tracker = BlockTracker()
    while not stop.is_set():
        notice = poll_once(client, tracker)
        if notice is not None:
            show(notice)
        stop.wait(POLL_SECONDS)


def start_polling(
    client: IpcClient,
    post: Callable[[Callable[[], None]], None],
    show: Callable[[BlockNotice], None],
) -> threading.Event:
    stop = threading.Event()
    threading.Thread(
        target=poll_loop,
        args=(client, lambda notice: post(lambda: show(notice)), stop),
        name="webfilter",
        daemon=True,
    ).start()
    return stop
