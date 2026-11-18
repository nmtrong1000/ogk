import threading

from tray.features.presence import heartbeat as heartbeat_module
from tray.features.presence.icon import TOOLTIP, create_icon
from tray.features.presence.window import describe
from tray.ipc_client import IpcError


def test_icon_has_tooltip_and_no_quit_item():
    icon = create_icon(on_open=lambda: None)
    assert icon.title == TOOLTIP
    assert "OGK đang chạy" in TOOLTIP
    assert [item.text for item in icon.menu.items] == ["Mở OGK"]


def test_describe_shows_supervision_state():
    on = describe({"uptime": 1, "server_reachable": True, "enforcement": {"enabled": True}})
    off = describe({"uptime": 1, "server_reachable": True, "enforcement": {"enabled": False}})
    assert "Giám sát: đang bật" in on
    assert "Giám sát: đã tắt" in off
    assert "Giám sát: không rõ" in describe({})


class FakeClient:
    def __init__(self, stop, fail_first):
        self.calls = 0
        self.stop = stop
        self.fail_first = fail_first

    def heartbeat(self):
        self.calls += 1
        if self.calls >= 3:
            self.stop.set()
        if self.fail_first and self.calls == 1:
            raise IpcError("not_running", "down")


def test_heartbeat_loop_keeps_going_after_errors():
    stop = threading.Event()
    client = FakeClient(stop, fail_first=True)
    heartbeat_module.heartbeat_loop(client, stop, interval=0.001)
    assert client.calls == 3
