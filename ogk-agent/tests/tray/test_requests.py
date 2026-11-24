from tray.features.requests.logic import DecisionTracker, decision_text


def _result(request_id=1, *, status="approved", kind="add_time", domain=None, message=None):
    return {
        "id": request_id,
        "status": status,
        "type": kind,
        "domain": domain,
        "message": message,
    }


def test_tracker_shows_latest_decision_after_tray_restart_then_only_new_decisions():
    tracker = DecisionTracker()
    assert len(tracker.update([_result(1), _result(2, kind="blocked_domain", domain="school.example")])) == 1
    assert tracker.update([_result(1), _result(2, kind="blocked_domain", domain="school.example")]) == []
    decisions = tracker.update([_result(1), _result(2), _result(3, status="rejected")])
    assert len(decisions) == 1
    assert decisions[0].request_id == 3
    assert "chưa được duyệt" in decisions[0].text


def test_decision_text_includes_parent_message_and_domain():
    text = decision_text(_result(kind="blocked_domain", domain="school.example", message="Đã mở nhé"))
    assert "school.example" in text
    assert "Đã mở nhé" in text
