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

    def heartbeat(self, idle_seconds=None, foreground=None):
        self.calls += 1
        self.idle = idle_seconds
        self.apps = [*getattr(self, "apps", []), foreground]
        if self.calls >= 3:
            self.stop.set()
        if self.fail_first and self.calls == 1:
            raise IpcError("not_running", "down")


def test_heartbeat_loop_keeps_going_after_errors():
    stop = threading.Event()
    client = FakeClient(stop, fail_first=True)
    heartbeat_module.heartbeat_loop(client, stop, interval=0.001)
    assert client.calls == 3


def test_heartbeat_sends_idle_time():
    stop = threading.Event()
    client = FakeClient(stop, fail_first=False)
    heartbeat_module.heartbeat_loop(client, stop, interval=0.001, idle=lambda: 312.0)
    assert client.idle == 312.0


def test_unreadable_idle_time_is_left_out():
    def broken() -> float:
        raise OSError("no input info")

    stop = threading.Event()
    client = FakeClient(stop, fail_first=False)
    heartbeat_module.heartbeat_loop(client, stop, interval=0.001, idle=broken)
    assert client.idle is None


def test_extra_menu_items_follow_open():
    icon = create_icon(on_open=lambda: None, extra=[("Thời gian còn lại", lambda: None)])
    assert [item.text for item in icon.menu.items] == ["Mở OGK", "Thời gian còn lại"]


def test_heartbeat_sends_foreground_app():
    stop = threading.Event()
    client = FakeClient(stop, fail_first=False)
    heartbeat_module.heartbeat_loop(client, stop, interval=0.001, foreground=lambda: "chrome.exe")
    assert client.apps == ["chrome.exe"] * 3


def test_foreground_change_is_sent_before_interval():
    stop = threading.Event()
    client = FakeClient(stop, fail_first=False)
    apps = iter(["a.exe", "a.exe", "b.exe", None, "c.exe"])
    heartbeat_module.heartbeat_loop(client, stop, interval=60, foreground=lambda: next(apps), check=0.001)
    assert client.apps == ["a.exe", "b.exe", None]


def test_broken_foreground_reader_sends_none():
    def broken():
        raise OSError("denied")

    stop = threading.Event()
    client = FakeClient(stop, fail_first=False)
    heartbeat_module.heartbeat_loop(client, stop, interval=0.001, foreground=broken)
    assert client.apps == [None] * 3
