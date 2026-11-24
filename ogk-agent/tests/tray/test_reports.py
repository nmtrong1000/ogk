import asyncio
import json
import threading

import pytest

from service.core.ipc_server import IpcServer
from tray.features.reports import failure_text
from tray.features.reports.opener import fetch_and_open
from tray.ipc_client import IpcClient, IpcError
from tray.platform import fake

LINK = "https://192.168.100.238:8443/child-view/start#code=" + "c" * 43


def run_service(tmp_path, handler):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    server = IpcServer(tmp_path, 0, dict, child_view_handler=handler)
    asyncio.run_coroutine_threadsafe(server.start(), loop).result(5)

    def stop():
        asyncio.run_coroutine_threadsafe(server.stop(), loop).result(5)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)
        loop.close()

    return stop


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def child_view_link(self):
        if self.error:
            raise IpcError(self.error, "refused")
        return self.result


def test_link_is_opened_without_notice():
    opened, notices = [], []
    client = FakeClient({"status": "ok", "url": LINK})
    assert fetch_and_open(client, lambda u: opened.append(u) or True, lambda *a: notices.append(a))
    assert opened == [LINK]
    assert notices == []


@pytest.mark.parametrize(
    ("error", "text"),
    [
        ("no_child", "Tài khoản này chưa được gắn với bạn nhỏ nào nên chưa có báo cáo."),
        ("not_running", "OGK chưa chạy. Em hãy thử lại sau ít phút."),
        ("child_view_failed", "Chưa mở được báo cáo. Em hãy thử lại sau."),
    ],
)
def test_service_errors_become_child_friendly_notices(error, text):
    notices = []
    assert not fetch_and_open(FakeClient(error=error), lambda u: True, lambda *a: notices.append(a))
    assert notices == [("OGK - Báo cáo của em", text)]


def test_non_https_link_is_not_opened():
    opened, notices = [], []
    result = fetch_and_open(FakeClient({"url": "http://evil/x"}), opened.append, lambda *a: notices.append(a))
    assert not result and opened == []
    assert notices[0][1] == failure_text("bad_response")


def test_browser_failure_is_reported():
    notices = []
    assert not fetch_and_open(FakeClient({"url": LINK}), lambda u: False, lambda *a: notices.append(a))
    assert notices[0][1] == failure_text("browser_failed")


def test_client_passes_through_child_view_errors(tmp_path):
    outcomes = [{"url": LINK}, LookupError()]

    async def issue():
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    stop = run_service(tmp_path, issue)
    try:
        client = IpcClient(tmp_path)
        assert client.child_view_link() == {"status": "ok", "url": LINK}
        with pytest.raises(IpcError) as info:
            client.child_view_link()
        assert info.value.code == "no_child"
    finally:
        stop()


def test_fake_open_url_records_instead_of_opening(tmp_path, monkeypatch):
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path))
    assert fake.open_url(LINK)
    lines = (tmp_path / fake.BROWSER_FILE).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [{"url": LINK}]
