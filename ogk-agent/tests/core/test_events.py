"""docs/test_vectors.json is shared with ogk-server; both sides must accept and reject the same events."""

import pytest

from service.core.events import EVENT_FIELDS, EventInvalid, validate_event
from tests.policy_vectors import EVENT_VECTORS


@pytest.mark.parametrize("case", EVENT_VECTORS["valid"], ids=lambda c: c["name"])
def test_valid_event_vectors(case):
    assert validate_event(case["event"]) == case["event"]


@pytest.mark.parametrize("case", EVENT_VECTORS["invalid"], ids=lambda c: c["name"])
def test_invalid_event_vectors(case):
    with pytest.raises(EventInvalid) as exc:
        validate_event(case["event"])
    assert exc.value.field == case["field"]


def test_vectors_use_the_seven_fields():
    for case in EVENT_VECTORS["valid"]:
        assert tuple(case["event"]) == EVENT_FIELDS


def test_rejects_non_object():
    with pytest.raises(EventInvalid) as exc:
        validate_event(["not", "an", "event"])
    assert exc.value.field is None
