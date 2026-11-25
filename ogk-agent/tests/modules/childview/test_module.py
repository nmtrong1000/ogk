from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import pytest

from service.modules.childview.module import ChildViewModule

pytestmark = pytest.mark.anyio


class FakeSession:
    def __init__(self, fail_first=False):
        self.calls = []
        self.fresh_calls = []
        self.fail_first = fail_first

    async def create_child_view_code(self, child_id, code):
        self.calls.append((child_id, code))
        if self.fail_first:
            self.fail_first = False
            raise httpx.RemoteProtocolError("Server disconnected")
        return {"expires_at": "2026-11-19T08:01:00Z"}

    async def create_child_view_code_fresh(self, child_id, code):
        self.fresh_calls.append((child_id, code))
        return {"expires_at": "2026-11-19T08:01:00Z"}


def context(session, child_id):
    return SimpleNamespace(
        session=session,
        screen=SimpleNamespace(child_id=child_id),
        config=SimpleNamespace(server_url="https://192.168.100.238:8443/"),
    )


async def test_link_carries_a_fresh_code_for_the_signed_in_child_in_the_fragment():
    session = FakeSession()
    module = ChildViewModule(context(session, 9))
    first = await module.issue_child_view_link()
    second = await module.issue_child_view_link()
    parts = urlsplit(first["url"])
    expected = ("https", "192.168.100.238:8443", "/child-view/start", "")
    assert (parts.scheme, parts.netloc, parts.path, parts.query) == expected
    assert parts.fragment == f"code={session.calls[0][1]}"
    assert [child for child, _ in session.calls] == [9, 9]
    assert session.calls[0][1] != session.calls[1][1]
    assert len(session.calls[0][1]) >= 32
    assert first["expires_at"] == "2026-11-19T08:01:00Z"
    assert second["url"] != first["url"]


async def test_no_signed_in_child_raises_lookup_error():
    session = FakeSession()
    with pytest.raises(LookupError):
        await ChildViewModule(context(session, None)).issue_child_view_link()
    assert session.calls == []


async def test_not_enrolled_raises_runtime_error():
    with pytest.raises(RuntimeError):
        await ChildViewModule(context(None, 9)).issue_child_view_link()


async def test_transient_disconnect_retries_with_fresh_connection_and_code():
    session = FakeSession(fail_first=True)
    link = await ChildViewModule(context(session, 9)).issue_child_view_link()
    code = urlsplit(link["url"]).fragment.removeprefix("code=")
    assert session.calls[0][0] == 9
    assert session.fresh_calls == [(9, code)]
    assert session.calls[0][1] != code
