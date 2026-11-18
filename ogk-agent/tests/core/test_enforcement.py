import logging

from service.core.enforcement import Enforcement


def test_starts_enabled():
    snapshot = Enforcement().snapshot()
    assert snapshot["enabled"] is True
    assert snapshot["reason"] is None
    assert snapshot["since"].endswith("Z")


def test_disable_and_enable_log_only_on_change(caplog):
    caplog.set_level(logging.INFO)
    enforcement = Enforcement()
    enforcement.enable()
    enforcement.disable("tray_unavailable")
    enforcement.disable("tray_unavailable")
    assert enforcement.snapshot()["enabled"] is False
    assert enforcement.snapshot()["reason"] == "tray_unavailable"
    enforcement.enable()
    enforcement.enable()
    assert enforcement.enabled
    assert caplog.text.count("enforcement disabled: tray_unavailable") == 1
    assert caplog.text.count("enforcement enabled again") == 1
