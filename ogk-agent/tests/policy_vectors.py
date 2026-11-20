"""Loads docs/test_vectors.json, shared with ogk-server. Its key is test-only, so tests may sign with it."""

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from service.core.policy_store import canonical_json

VECTORS = json.loads((Path(__file__).resolve().parents[2] / "docs" / "test_vectors.json").read_text(encoding="utf-8"))
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(VECTORS["key"]["test_only_private_seed_hex"]))
PUBLIC_KEY_PEM = VECTORS["key"]["public_key_pem"]
EVENT_VECTORS = VECTORS["events"]


def write_public_key(directory: Path) -> Path:
    path = directory / "policy_public.pem"
    path.write_text(PUBLIC_KEY_PEM, encoding="utf-8")
    return path


OPEN_DAY = "1" * 48
ALLOWED_DAY = "0" * 14 + "1" * 28 + "0" * 6


def rules(
    quota: int = 120,
    weekend: int | None = None,
    schedule: list[str] | None = None,
    app_rules: list[dict] | None = None,
) -> dict:
    return {
        "weekday_quota_minutes": quota,
        "weekend_quota_minutes": quota if weekend is None else weekend,
        "weekly_schedule": [ALLOWED_DAY] * 7 if schedule is None else schedule,
        "app_rules": [] if app_rules is None else app_rules,
    }


def document(
    child_id: int,
    version: int,
    quota: int = 120,
    *,
    accounts: list[str] | None = None,
    weekend: int | None = None,
    schedule: list[str] | None = None,
    app_rules: list[dict] | None = None,
    set_by: str = "parent@example.com",
) -> dict:
    return {
        "accounts": [] if accounts is None else accounts,
        "child_id": child_id,
        "format": 1,
        "issued_at": "2026-11-18T08:00:00Z",
        "policy_version": version,
        "rules": rules(quota, weekend, schedule, app_rules),
        "set_by": set_by,
    }


def envelope(doc: dict, key: Ed25519PrivateKey = PRIVATE_KEY) -> dict:
    signature = base64.urlsafe_b64encode(key.sign(canonical_json(doc))).rstrip(b"=").decode()
    return {"policy": doc, "signature": signature, "key_id": VECTORS["key"]["key_id"]}


def body(*docs: dict) -> dict:
    return {"policies": [envelope(doc) for doc in docs]}
