"""Must accept and reject exactly what ogk-server app/modules/sync/service.py does (checked by
docs/test_vectors.json); an event the server rejects makes it drop the whole batch.
The server also checks that device_id is the caller and child_id belongs to the same parent; the agent cannot.
"""

import re
from datetime import UTC, datetime
from typing import Any

EVENT_FIELDS = ("ts", "device_id", "child_id", "type", "subject", "duration_sec", "policy_id")
EVENT_TYPES = (
    "app_start",
    "app_stop",
    "domain_query",
    "blocked_app",
    "blocked_domain",
    "quota_warning",
    "locked",
    "unlock_request",
    "override_granted",
)
DOMAIN_TYPES = ("domain_query", "blocked_domain")
MAX_SUBJECT = 255
MAX_DURATION_SEC = 86400
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TS_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
DOMAIN_PATTERN = re.compile(
    r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


class EventInvalid(ValueError):
    def __init__(self, field: str | None) -> None:
        super().__init__(f"invalid event field: {field}")
        self.field = field


def format_ts(at: datetime) -> str:
    return at.astimezone(UTC).strftime(TS_FORMAT)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _ts_ok(value: Any) -> bool:
    if not isinstance(value, str) or not TS_PATTERN.fullmatch(value):
        return False
    try:
        datetime.strptime(value, TS_FORMAT)
    except ValueError:
        return False
    return True


def _subject_ok(event_type: str, subject: Any) -> bool:
    if not isinstance(subject, str) or len(subject) > MAX_SUBJECT or "/" in subject or "\\" in subject:
        return False
    if event_type in DOMAIN_TYPES:
        return DOMAIN_PATTERN.fullmatch(subject) is not None
    return True


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EventInvalid(None)
    for key in event:
        if key not in EVENT_FIELDS:
            raise EventInvalid(key)
    for key in EVENT_FIELDS:
        if key not in event:
            raise EventInvalid(key)
    if not _ts_ok(event["ts"]):
        raise EventInvalid("ts")
    if not _is_int(event["device_id"]):
        raise EventInvalid("device_id")
    if not _is_int(event["child_id"]):
        raise EventInvalid("child_id")
    if event["type"] not in EVENT_TYPES:
        raise EventInvalid("type")
    if not _subject_ok(event["type"], event["subject"]):
        raise EventInvalid("subject")
    if not _is_int(event["duration_sec"]) or not 0 <= event["duration_sec"] <= MAX_DURATION_SEC:
        raise EventInvalid("duration_sec")
    if not _is_int(event["policy_id"]) or event["policy_id"] < 0:
        raise EventInvalid("policy_id")
    return {key: event[key] for key in EVENT_FIELDS}
