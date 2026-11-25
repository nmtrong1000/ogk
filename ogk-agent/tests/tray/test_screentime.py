import json

from tray.features.screentime import Tracker
from tray.features.screentime.logic import format_duration, remaining_text, tray_tooltip_text
from tray.features.screentime.poller import poll_once
from tray.ipc_client import IpcError
from tray.platform import fake


def snap(**fields) -> dict:
    base = {
        "child_id": 7,
        "state": "ok",
        "remaining_seconds": 3600,
        "warning": None,
        "warning_seq": 0,
        "grace_seconds": None,
        "lock_reason": None,
        "lock_seq": 0,
        "set_by": "parent@example.com",
    }
    return {**base, **fields}


def test_remaining_clock_text():
    assert format_duration(3725) == "01:02:05"
    assert remaining_text(snap(remaining_seconds=59)) == "Còn lại 00:00:59"
    assert "Không có giới hạn" in remaining_text(snap(child_id=None, state="none"))
    assert "khóa sau 42 giây" in remaining_text(snap(state="grace", grace_seconds=42))


def test_remaining_clock_shows_category_budgets():
    text = remaining_text(
        snap(
            group_remaining=[
                {"name": "Trò chơi", "remaining_seconds": 2700},
                {"name": "Học tập", "remaining_seconds": None},
            ]
        )
    )
    assert "Trò chơi: 00:45:00" in text
    assert "Học tập: Không giới hạn" in text


def test_tray_tooltip_stays_within_windows_limit_and_uses_summary():
    text = remaining_text(snap(group_remaining=[{"name": "Trò chơi", "remaining_seconds": 2700}] * 7))
    tooltip = tray_tooltip_text("OGK đang chạy", text)
    assert len(tooltip) <= 127
    assert "Thời gian theo nhóm ứng dụng" not in tooltip


def test_each_warning_is_shown_once():
    tracker = Tracker()
    assert tracker.update(snap()).notify is None
    plans = [tracker.update(snap(warning=m, warning_seq=i + 1)) for i, m in enumerate((10, 5, 1))]
    assert [p.notify[1] for p in plans] == [
        "Còn 10 phút dùng máy. Hãy lưu bài đang làm.",
        "Còn 5 phút dùng máy. Hãy lưu bài đang làm.",
        "Còn 1 phút dùng máy. Hãy lưu bài đang làm.",
    ]
    assert tracker.update(snap(warning=1, warning_seq=3)).notify is None


def test_restarted_tray_does_not_replay_old_warning():
    assert Tracker().update(snap(warning=5, warning_seq=2)).notify is None


def test_grace_countdown_text():
    plan = Tracker().update(snap(state="grace", grace_seconds=37, lock_reason="quota"))
    assert "Máy sẽ khóa sau 37 giây" in plan.grace
    assert plan.lock is None


def test_lock_shows_reason_and_setter_once_per_order():
    tracker = Tracker()
    locked = snap(state="locked", lock_reason="schedule", lock_seq=1)
    order = tracker.update(locked).lock
    assert order.seq == 1
    assert "ngoài khung giờ" in order.text
    assert "Người đặt luật: parent@example.com" in order.text
    assert tracker.update(locked).lock is None
    assert tracker.update({**locked, "lock_seq": 2}).lock.seq == 2


def test_parent_commands_notify_once():
    tracker = Tracker()
    assert tracker.update(snap(command_seq=0)).notify is None
    locked = tracker.update(snap(command_seq=1, command_type="lock", state="locked", lock_seq=1))
    assert locked.notify == ("Phụ huynh khóa máy", "Phụ huynh vừa gửi lệnh khóa máy.")
    assert tracker.update(snap(command_seq=1, command_type="lock", state="locked", lock_seq=1)).notify is None
    unlocked = tracker.update(snap(command_seq=2, command_type="unlock"))
    assert unlocked.notify == ("Phụ huynh mở khóa máy", "Phụ huynh đã mở khóa máy cho bạn.")
    added = tracker.update(snap(command_seq=3, command_type="add_time"))
    assert added.notify == ("Được cộng thêm thời gian", "Phụ huynh đã cộng 15 phút sử dụng máy.")


def test_restarted_tray_obeys_existing_lock():
    order = Tracker().update(snap(state="locked", lock_reason="quota", lock_seq=4, set_by="")).lock
    assert order is not None
    assert "Người đặt luật: Phụ huynh" in order.text


class Client:
    def __init__(self, result):
        self.result = result

    def screentime(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_unreachable_service_applies_nothing():
    assert poll_once(Client(IpcError("not_running", "down")), Tracker()) is None
    assert poll_once(Client(snap()), Tracker()).remaining == "Còn lại 01:00:00"


def test_fake_lock_records_order_and_locks_fake_session(tmp_path, monkeypatch):
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path))
    assert fake.lock_workstation()
    assert json.loads((tmp_path / "fake_lock.jsonl").read_text().splitlines()[0])["ts"].endswith("Z")
    assert json.loads((tmp_path / "fake_session.jsonl").read_text()) == {"event": "lock", "session_id": 1}


def test_fake_idle_reads_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path))
    assert fake.idle_seconds() == 0.0
    (tmp_path / "fake_idle").write_text("400\n")
    assert fake.idle_seconds() == 400.0
    (tmp_path / "fake_idle").write_text("x")
    assert fake.idle_seconds() == 0.0
