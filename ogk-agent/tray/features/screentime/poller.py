"""Polls on its own thread and hands each Plan to the Tk thread through post, so Tk is never touched here.
While the service is unreachable nothing is applied: the service, not the Tray UI, decides when to lock.
"""

import threading
from collections.abc import Callable

from tray.features.screentime.logic import Plan, Tracker
from tray.ipc_client import IpcClient, IpcError

POLL_SECONDS = 1.0


def poll_once(client: IpcClient, tracker: Tracker) -> Plan | None:
    try:
        snapshot = client.screentime()
    except IpcError:
        return None
    return tracker.update(snapshot)


def poll_loop(
    client: IpcClient, apply: Callable[[Plan], None], stop: threading.Event, interval: float = POLL_SECONDS
) -> None:
    tracker = Tracker()
    while not stop.is_set():
        plan = poll_once(client, tracker)
        if plan is not None:
            apply(plan)
        stop.wait(interval)


def start_polling(
    client: IpcClient, post: Callable[[Callable[[], None]], None], apply: Callable[[Plan], None]
) -> threading.Event:
    stop = threading.Event()

    def hand_over(plan: Plan) -> None:
        post(lambda: apply(plan))

    threading.Thread(target=poll_loop, args=(client, hand_over, stop), name="screentime", daemon=True).start()
    return stop
