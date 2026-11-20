import logging
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from service.core.local_db import DB_FILE, LocalDb
from service.core.policy_store import PolicyRejected, PolicyStore, canonical_json, load_public_key, verify_document
from tests.policy_vectors import VECTORS, body, document, envelope, write_public_key


@pytest.fixture
def store(data_dir):
    return PolicyStore(LocalDb(data_dir), write_public_key(data_dir))


@pytest.mark.parametrize("case", VECTORS["canonical"])
def test_canonical_form_matches_server(case):
    assert canonical_json(case["input"]) == case["canonical"].encode()


@pytest.mark.parametrize("case", VECTORS["valid"], ids=lambda c: c["name"])
def test_valid_vectors(case, data_dir):
    key = load_public_key(write_public_key(data_dir))
    assert canonical_json(case["policy"]) == case["canonical"].encode()
    policy = verify_document(key, case["policy"], case["signature"])
    assert (policy.child_id, policy.version) == (case["policy"]["child_id"], case["policy"]["policy_version"])


@pytest.mark.parametrize("case", VECTORS["invalid"], ids=lambda c: c["name"])
def test_invalid_vectors(case, data_dir):
    key = load_public_key(write_public_key(data_dir))
    with pytest.raises(PolicyRejected):
        verify_document(key, case["policy"], case["signature"])


@pytest.mark.parametrize("case", VECTORS["invalid_rules"], ids=lambda c: c["name"])
def test_signed_but_malformed_rules_rejected(case, data_dir):
    key = load_public_key(write_public_key(data_dir))
    with pytest.raises(PolicyRejected):
        verify_document(key, case["policy"], case["signature"])


def test_malformed_rules_reject_whole_batch(store):
    store.save(body(document(7, 3)))
    bad = document(8, 1)
    bad["rules"]["weekly_schedule"] = ["1" * 48] * 6
    with pytest.raises(PolicyRejected):
        store.save(body(document(7, 4), bad))
    assert store.versions() == {7: 3}


def test_child_for_sid_uses_signed_accounts(store):
    store.save(body(document(7, 3, accounts=["S-1-5-21-1", "S-1-5-21-2"]), document(8, 1, accounts=["S-1-5-21-3"])))
    assert store.child_for_sid("S-1-5-21-2") == 7
    assert store.child_for_sid("S-1-5-21-3") == 8
    assert store.child_for_sid("S-1-5-21-9") is None
    assert store.child_for_sid("") is None
    assert store.rules_for(7).set_by == "parent@example.com"


def test_save_then_load_from_db(store, data_dir):
    store.save(body(document(7, 3), document(8, 1)))
    fresh = PolicyStore(LocalDb(data_dir), write_public_key(data_dir))
    assert fresh.load().keys() == {7, 8}
    assert fresh.versions() == {7: 3, 8: 1}


def test_one_byte_changed_in_db_is_rejected(store, data_dir, caplog):
    store.save(body(document(7, 3, quota=120), document(8, 1)))
    with sqlite3.connect(data_dir / DB_FILE) as conn:
        conn.execute("UPDATE policies SET payload = replace(payload, '120', '920') WHERE child_id = 7")
    fresh = PolicyStore(LocalDb(data_dir), write_public_key(data_dir))
    with caplog.at_level(logging.WARNING, logger="ogk.policy"):
        assert fresh.load().keys() == {8}
    assert "policy for child 7 rejected: bad signature" in caplog.text


def test_row_columns_must_match_signed_document(store, data_dir):
    store.save(body(document(7, 3)))
    with sqlite3.connect(data_dir / DB_FILE) as conn:
        conn.execute("UPDATE policies SET version = 9 WHERE child_id = 7")
    assert PolicyStore(LocalDb(data_dir), write_public_key(data_dir)).load() == {}


def test_bad_signature_rejects_whole_batch(store):
    store.save(body(document(7, 1)))
    forged = envelope(document(8, 1), key=Ed25519PrivateKey.generate())
    with pytest.raises(PolicyRejected, match="bad signature"):
        store.save({"policies": [envelope(document(7, 2)), forged]})
    assert store.versions() == {7: 1}


def test_lower_version_is_refused(store):
    store.save(body(document(7, 3)))
    with pytest.raises(PolicyRejected, match="older"):
        store.save(body(document(7, 2)))
    assert store.versions() == {7: 3}


def test_save_compares_against_db_on_first_use(store, data_dir):
    store.save(body(document(7, 3)))
    fresh = PolicyStore(LocalDb(data_dir), write_public_key(data_dir))
    with pytest.raises(PolicyRejected):
        fresh.save(body(document(7, 2)))


def test_unassigned_child_is_dropped(store):
    store.save(body(document(7, 1), document(8, 1)))
    store.save(body(document(8, 1)))
    assert store.versions() == {8: 1}


@pytest.mark.parametrize("payload", [None, [], {"policies": None}, {"policies": ["x"]}, {"policies": [{}]}])
def test_malformed_response_rejected(store, payload):
    with pytest.raises(PolicyRejected):
        store.save(payload)


def test_missing_public_key_rejects_everything(data_dir, caplog):
    PolicyStore(LocalDb(data_dir), write_public_key(data_dir)).save(body(document(7, 1)))
    store = PolicyStore(LocalDb(data_dir), data_dir / "missing.pem")
    with caplog.at_level(logging.WARNING, logger="ogk.policy"):
        assert store.load() == {}
        with pytest.raises(PolicyRejected):
            store.save(body(document(7, 2)))
    assert "every policy is rejected" in caplog.text


def test_missing_app_rules_read_as_empty(store, data_dir):
    doc = document(7, 3, quota=90)
    del doc["rules"]["app_rules"]
    store.save(body(doc))
    restarted = PolicyStore(LocalDb(data_dir), write_public_key(data_dir))
    assert set(restarted.load()) == {7}
    policy = restarted.rules_for(7)
    assert policy.rules["app_rules"] == []
    assert policy.rules["weekday_quota_minutes"] == 90


def test_app_rules_of_wrong_type_still_rejected(store):
    doc = document(7, 3)
    doc["rules"]["app_rules"] = "x"
    with pytest.raises(PolicyRejected):
        store.save(body(doc))
