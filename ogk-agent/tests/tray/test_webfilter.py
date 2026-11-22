from tray.features.webfilter.logic import BlockTracker, notice_text


def _snapshot(seq=0, *, run_id="service-a", domain=None, reason="", set_by=""):
    return {
        "block_seq": seq,
        "run_id": run_id,
        "domain": domain,
        "reason": reason,
        "set_by": set_by,
    }


def test_tracker_ignores_initial_state_then_notifies_new_block():
    tracker = BlockTracker()

    assert tracker.update(_snapshot()) is None
    notice = tracker.update(
        _snapshot(1, domain="youtube.com", reason="danh sách tên miền bị chặn", set_by="Tom")
    )

    assert notice is not None
    assert notice.seq == 1
    assert "youtube.com" in notice.text
    assert "danh sách tên miền bị chặn" in notice.text
    assert "Tom" in notice.text


def test_tracker_notifies_only_new_sequence_in_same_service_run():
    tracker = BlockTracker()
    tracker.update(_snapshot(1, domain="blocked.example"))

    assert tracker.update(_snapshot(1, domain="blocked.example")) is None
    notice = tracker.update(_snapshot(2, domain="other.example"))
    assert notice is not None and notice.seq == 2


def test_tracker_notifies_new_block_after_service_restart():
    tracker = BlockTracker()
    tracker.update(_snapshot(3, run_id="service-a", domain="old.example"))

    notice = tracker.update(_snapshot(1, run_id="service-b", domain="new.example", set_by="Tom"))

    assert notice is not None
    assert "new.example" in notice.text


def test_notice_text_has_useful_defaults():
    text = notice_text(_snapshot(1))

    assert "website" in text
    assert "theo chính sách gia đình" in text
    assert "Phụ huynh" in text
