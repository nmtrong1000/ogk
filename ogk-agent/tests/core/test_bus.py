import logging

from service.core.bus import SESSION, Bus, SessionEvent


def test_publish_reaches_every_subscriber_of_topic():
    bus = Bus()
    seen = []
    bus.subscribe(SESSION, lambda event: seen.append(("a", event)))
    bus.subscribe(SESSION, lambda event: seen.append(("b", event)))
    bus.subscribe("other", lambda event: seen.append(("other", event)))
    event = SessionEvent("lock", 1)
    bus.publish(SESSION, event)
    assert seen == [("a", event), ("b", event)]


def test_failing_handler_is_logged_and_others_still_run(caplog):
    bus = Bus()
    seen = []

    def boom(_):
        raise RuntimeError("boom")

    bus.subscribe(SESSION, boom)
    bus.subscribe(SESSION, seen.append)
    with caplog.at_level(logging.ERROR):
        bus.publish(SESSION, 1)
    assert seen == [1]
    assert "handler for session failed" in caplog.text


def test_publish_without_subscribers_is_noop():
    Bus().publish("nobody")
