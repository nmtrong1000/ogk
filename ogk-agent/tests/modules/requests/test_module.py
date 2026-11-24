import pytest

from service.modules.requests.module import RequestsModule


class FakeSession:
    device_id = 17

    def __init__(self):
        self.body = None

    async def create_request(self, body):
        self.body = body
        return {"id": 4, "status": "pending"}


class FakeQueue:
    def __init__(self):
        self.events = []

    async def enqueue(self, events):
        self.events.extend(events)


class FakeStore:
    def versions(self):
        return {9: 3}


@pytest.mark.anyio
async def test_submit_uses_active_child_and_records_unlock_request():
    session = FakeSession()
    queue = FakeQueue()
    context = type(
        "Context",
        (),
        {
            "session": session,
            "screen": type("Screen", (), {"child_id": 9})(),
            "event_queue": queue,
            "policy_store": FakeStore(),
        },
    )()
    result = await RequestsModule(context).submit({"type": "add_time"})
    assert result["id"] == 4
    assert session.body == {"child_id": 9, "type": "add_time"}
    assert queue.events[0]["type"] == "unlock_request"
    assert queue.events[0]["child_id"] == 9
