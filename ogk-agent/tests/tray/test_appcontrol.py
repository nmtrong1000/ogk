import threading

from tray.features.appcontrol import BlockTracker
from tray.features.appcontrol import poller as poller_module
from tray.features.appcontrol.logic import DEFAULT_POLICY_SETTER, BlockNotice, NotificationGate, notice_text
from tray.ipc_client import IpcError


def snap(
    seq: int,
    app: str | None = "game.exe",
    set_by: str = "parent@example.com",
    source: str = "cached",
    run_id: str = "run-1",
) -> dict:
    return {"status": "ok", "block_seq": seq, "app": app, "set_by": set_by, "source": source, "run_id": run_id}


def test_first_snapshot_is_only_a_baseline():
    tracker = BlockTracker()
    assert tracker.update(snap(4)) is None
    assert tracker.update(snap(4)) is None
    notice = tracker.update(snap(5))
    assert notice.seq == 5
    assert "game.exe" in notice.text and "parent@example.com" in notice.text


def test_baseline_zero_then_block_shows():
    tracker = BlockTracker()
    tracker.update(snap(0, app=None))
    assert tracker.update(snap(1)) is not None


def test_service_restart_does_not_silence_blocks():
    tracker = BlockTracker()
    tracker.update(snap(3))
    assert tracker.update(snap(0, app=None, run_id="run-2")) is None
    notice = tracker.update(snap(1, run_id="run-2"))
    assert notice is not None and notice.seq == 1


def test_service_restart_with_a_block_already_made_shows_it():
    tracker = BlockTracker()
    tracker.update(snap(3))
    assert tracker.update(snap(2, run_id="run-2")) is not None


def test_bad_snapshot_ignored():
    tracker = BlockTracker()
    assert tracker.update({"block_seq": "1"}) is None
    assert tracker.update({"block_seq": True}) is None


def test_default_policy_setter_text():
    assert DEFAULT_POLICY_SETTER in notice_text(snap(1, set_by="", source="default"))
    assert "Phụ huynh" in notice_text(snap(1, set_by=""))


def test_group_budget_notice_explains_the_group():
    text = notice_text({**snap(1), "reason": "group_budget:Trò chơi"})
    assert "đã hết thời gian của nhóm Trò chơi" in text


def test_block_notifications_are_throttled_per_message():
    now = [10.0]
    gate = NotificationGate(interval=60, monotonic=lambda: now[0])
    game = BlockNotice(1, "Trò chơi đã hết giờ")
    study = BlockNotice(2, "Ứng dụng bị chặn")
    assert gate.allow(game)
    assert not gate.allow(game)
    assert gate.allow(study)
    now[0] = 70.0
    assert gate.allow(game)


class FakeClient:
    def __init__(self, snapshots, stop):
        self.snapshots = list(snapshots)
        self.stop = stop

    def appcontrol(self):
        if not self.snapshots:
            self.stop.set()
            raise IpcError("unreachable", "down")
        item = self.snapshots.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_poll_loop_shows_each_new_block_once():
    stop = threading.Event()
    client = FakeClient([snap(1), IpcError("unreachable", "x"), snap(2), snap(2), snap(3)], stop)
    shown = []
    poller_module.poll_loop(client, shown.append, stop, interval=0.001)
    assert [n.seq for n in shown] == [2, 3]
