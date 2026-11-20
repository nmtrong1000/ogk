"""docs/test_vectors.json is shared with ogk-agent; both sides must produce the same bytes and signatures."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core import signing
from app.modules.policy.models import Policy
from app.modules.policy.service import document, dump_app_rules

VECTORS = json.loads((Path(__file__).resolve().parents[3] / "docs" / "test_vectors.json").read_text(encoding="utf-8"))
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(VECTORS["key"]["test_only_private_seed_hex"]))
PUBLIC_KEY = serialization.load_pem_public_key(VECTORS["key"]["public_key_pem"].encode())


def test_public_key_and_key_id_match_seed():
    assert signing.raw_public_key(PUBLIC_KEY) == signing.raw_public_key(PRIVATE_KEY.public_key())
    assert signing.key_id(PUBLIC_KEY) == VECTORS["key"]["key_id"]


@pytest.mark.parametrize("case", VECTORS["canonical"])
def test_canonical_form(case):
    assert signing.canonical_json(case["input"]) == case["canonical"].encode()


@pytest.mark.parametrize("case", VECTORS["valid"], ids=lambda c: c["name"])
def test_valid_vectors(case):
    assert signing.canonical_json(case["policy"]) == case["canonical"].encode()
    assert signing.sign_with(PRIVATE_KEY, case["policy"]) == case["signature"]
    assert signing.verify(PUBLIC_KEY, case["policy"], case["signature"])


@pytest.mark.parametrize("case", VECTORS["invalid"], ids=lambda c: c["name"])
def test_invalid_vectors(case):
    assert not signing.verify(PUBLIC_KEY, case["policy"], case["signature"])


@pytest.mark.parametrize("case", VECTORS["invalid_rules"], ids=lambda c: c["name"])
def test_invalid_rules_are_signed_correctly(case):
    assert signing.verify(PUBLIC_KEY, case["policy"], case["signature"])


def test_server_document_matches_vector_shape():
    expected = VECTORS["valid"][0]["policy"]
    policy = Policy(
        child_id=7,
        version=3,
        weekday_quota_minutes=120,
        weekend_quota_minutes=180,
        weekly_schedule="".join(expected["rules"]["weekly_schedule"]),
        app_rules=dump_app_rules(expected["rules"]["app_rules"]),
        updated_at=datetime(2026, 11, 18, 8, tzinfo=UTC),
    )
    assert document(policy, expected["accounts"], expected["set_by"]) == expected
