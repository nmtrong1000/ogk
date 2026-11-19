import pytest

from service.core.device_session import DeviceSession
from service.core.event_queue import EventQueue
from service.core.events import EventInvalid
from service.core.local_db import LocalDb
from tests.core.test_device_session import CONFIG, enrolled
from tests.fake_server import FakeServer
from tests.policy_vectors import EVENT_VECTORS

pytestmark = pytest.mark.anyio

SAMPLE = EVENT_VECTORS["valid"][0]["event"]


@pytest.fixture
def server():
    return FakeServer()


def make_queue(server: FakeServer, data_dir, batch_size: int = 500) -> EventQueue:
    db = LocalDb(data_dir)
    enrolled(server, db)
    session = DeviceSession(CONFIG, db, client_factory=server.client, clock=lambda: server.now)
    return EventQueue(db, session, batch_size=batch_size)


def events(n: int) -> list[dict]:
    return [{**SAMPLE, "duration_sec": i} for i in range(n)]


async def test_sends_and_clears_queue(server, data_dir):
    queue = make_queue(server, data_dir)
    await queue.enqueue(events(3))
    assert await queue.flush() == 3
    assert [e["duration_sec"] for e in server.events] == [0, 1, 2]
    assert await queue.pending() == 0


async def test_rejects_invalid_event_before_storing(server, data_dir):
    queue = make_queue(server, data_dir)
    with pytest.raises(EventInvalid):
        await queue.enqueue([SAMPLE, {**SAMPLE, "type": "screenshot"}])
    assert await queue.pending() == 0


async def test_outage_keeps_events_until_network_returns(server, data_dir):
    queue = make_queue(server, data_dir, batch_size=2)
    await queue.enqueue(events(3))
    server.offline = True
    assert await queue.flush() == 0
    await queue.enqueue(events(1))
    assert await queue.pending() == 4
    server.offline = False
    assert await queue.flush() == 4
    assert len(server.events) == 4
    assert len(server.batch_keys) == 2


async def test_lost_response_resends_same_key_and_is_not_counted_twice(server, data_dir):
    queue = make_queue(server, data_dir)
    await queue.enqueue(events(2))
    server.drop_response = True
    assert await queue.flush() == 0
    assert await queue.pending() == 2
    server.drop_response = False
    await queue.enqueue(events(1))
    assert await queue.flush() == 3
    assert len(server.events) == 3
    assert len(server.batch_keys) == 2


async def test_restart_resends_with_stored_key(server, data_dir):
    queue = make_queue(server, data_dir)
    await queue.enqueue(events(2))
    server.drop_response = True
    await queue.flush()
    server.drop_response = False
    restarted = make_queue(server, data_dir)
    await restarted.flush()
    assert len(server.events) == 2
    assert len(server.batch_keys) == 1


async def test_batch_rejected_by_server_is_dropped(server, data_dir):
    queue = make_queue(server, data_dir)
    await queue.enqueue(events(2))
    server.reject_events = True
    assert await queue.flush() == 0
    assert await queue.pending() == 0


async def test_without_session_nothing_is_sent(data_dir):
    queue = EventQueue(LocalDb(data_dir), None)
    await queue.enqueue(events(1))
    assert await queue.flush() == 0
    assert await queue.pending() == 1
