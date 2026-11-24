import threading
from collections.abc import Callable

from tray.features.requests.logic import Decision, DecisionTracker
from tray.ipc_client import IpcClient, IpcError

POLL_SECONDS = 1.0


def poll_once(client: IpcClient, tracker: DecisionTracker) -> list[Decision]:
    try:
        snapshot = client.requests()
    except IpcError:
        return []
    return tracker.update(snapshot.get("results", []))


def poll_loop(client: IpcClient, show: Callable[[Decision], None], stop: threading.Event) -> None:
    tracker = DecisionTracker()
    while not stop.is_set():
        for decision in poll_once(client, tracker):
            show(decision)
        stop.wait(POLL_SECONDS)


def start_polling(
    client: IpcClient,
    post: Callable[[Callable[[], None]], None],
    show: Callable[[Decision], None],
) -> threading.Event:
    stop = threading.Event()
    threading.Thread(
        target=poll_loop,
        args=(client, lambda decision: post(lambda: show(decision)), stop),
        name="requests",
        daemon=True,
    ).start()
    return stop
