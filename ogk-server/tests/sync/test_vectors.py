"""docs/test_vectors.json is shared with ogk-agent; both sides must accept and reject the same events."""

import pytest

from app.core.errors import AppError
from app.modules.sync.service import EVENT_FIELDS, parse_event
from tests.sync.conftest import EVENT_VECTORS

DEVICE_ID = 3
CHILD_ID = 7


@pytest.mark.parametrize("case", EVENT_VECTORS["valid"], ids=lambda c: c["name"])
def test_valid_event_vectors(case):
    parsed = parse_event(case["event"], 0, DEVICE_ID, {CHILD_ID})
    assert set(parsed) == set(EVENT_FIELDS)
    assert parsed["ts"].tzinfo is not None


@pytest.mark.parametrize("case", EVENT_VECTORS["invalid"], ids=lambda c: c["name"])
def test_invalid_event_vectors(case):
    with pytest.raises(AppError) as exc:
        parse_event(case["event"], 4, DEVICE_ID, {CHILD_ID})
    assert exc.value.code == "invalid_event"
    assert exc.value.extra == {"index": 4, "field": case["field"]}


def test_vectors_use_the_seven_fields():
    for case in EVENT_VECTORS["valid"]:
        assert tuple(case["event"]) == EVENT_FIELDS
