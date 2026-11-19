import json
from datetime import UTC, datetime

import pytest

from service.core.bus import POLICY_MODE, Bus
from service.core.clock import SyncClock
from service.core.config import DEFAULT_POLICY_FILE, bundled_data_dir
from service.core.local_db import LocalDb
from service.core.offline import OfflineGuard
from service.core.policy_store import (
    MODE_CACHED,
    MODE_DEFAULT,
    PolicyRejected,
    PolicyStore,
    load_default_policy,
)
from tests.policy_vectors import body, document, write_public_key

DEFAULT = load_default_policy(bundled_data_dir() / DEFAULT_POLICY_FILE)
ALLOWED_DAY = "0" * 14 + "1" * 28 + "0" * 6


def test_shipped_default_policy_has_quota_and_weekly_schedule():
    assert DEFAULT.rules == {"daily_quota_minutes": 120, "weekly_schedule": [ALLOWED_DAY] * 7}


@pytest.mark.parametrize(
    "doc",
    [
        {"format": 2, "policy_version": 0, "rules": {}},
        {"format": 1, "policy_version": 1, "rules": {"daily_quota_minutes": 120, "weekly_schedule": [ALLOWED_DAY] * 7}},
        {
            "format": 1,
            "policy_version": 0,
            "rules": {"daily_quota_minutes": 2000, "weekly_schedule": [ALLOWED_DAY] * 7},
        },
        {"format": 1, "policy_version": 0, "rules": {"daily_quota_minutes": 120, "weekly_schedule": [ALLOWED_DAY] * 6}},
        {"format": 1, "policy_version": 0, "rules": {"daily_quota_minutes": 120, "weekly_schedule": ["2" * 48] * 7}},
    ],
)
def test_invalid_default_policy_rejected(tmp_path, doc):
    path = tmp_path / "default.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(PolicyRejected):
        load_default_policy(path)


def test_missing_default_policy_rejected(tmp_path):
    with pytest.raises(PolicyRejected):
        load_default_policy(tmp_path / "missing.json")


def make_store(data_dir) -> PolicyStore:
    store = PolicyStore(LocalDb(data_dir), write_public_key(data_dir), DEFAULT)
    store.save(body(document(7, 3, quota=45)))
    return store


def test_signed_policy_applies_while_fresh(data_dir):
    store = make_store(data_dir)
    assert store.mode == MODE_CACHED
    effective = store.rules_for(7)
    assert (effective.version, effective.rules, effective.source) == (3, {"daily_quota_minutes": 45}, MODE_CACHED)


def test_child_without_signed_policy_gets_default(data_dir):
    effective = make_store(data_dir).rules_for(99)
    assert (effective.version, effective.source) == (0, MODE_DEFAULT)


def test_expired_store_applies_default_to_every_child(data_dir):
    store = make_store(data_dir)
    assert store.set_expired(True)
    assert not store.set_expired(True)
    assert store.mode == MODE_DEFAULT
    assert {cid: (p.version, p.rules) for cid, p in store.effective().items()} == {7: (0, DEFAULT.rules)}
    assert store.versions() == {7: 3}


class Clocks:
    def __init__(self) -> None:
        self.mono = 0.0
        self.wall = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)


def test_seven_days_offline_switches_to_default_and_back(data_dir):
    clocks = Clocks()
    store = make_store(data_dir)
    bus = Bus()
    modes = []
    bus.subscribe(POLICY_MODE, modes.append)
    guard = OfflineGuard(SyncClock(LocalDb(data_dir), lambda: clocks.mono, lambda: clocks.wall), store, bus, 7)
    assert guard.start() == MODE_CACHED
    guard.online(clocks.wall)
    clocks.mono += 6 * 86400
    assert guard.offline() == MODE_CACHED
    clocks.mono += 86400
    assert guard.offline() == MODE_DEFAULT
    assert store.rules_for(7).source == MODE_DEFAULT
    guard.online(clocks.wall)
    assert store.mode == MODE_CACHED
    assert modes == [MODE_DEFAULT, MODE_CACHED]


def test_restart_after_long_outage_starts_in_default(data_dir):
    clocks = Clocks()
    db = LocalDb(data_dir)
    guard = OfflineGuard(SyncClock(db, lambda: clocks.mono, lambda: clocks.wall), make_store(data_dir), Bus(), 7)
    guard.start()
    guard.online(clocks.wall)
    clocks.wall = clocks.wall.replace(day=27)
    store = make_store(data_dir)
    restarted = OfflineGuard(SyncClock(db, lambda: 0.0, lambda: clocks.wall), store, Bus(), 7)
    assert restarted.start() == MODE_DEFAULT


def test_simulated_days_switch_to_default(data_dir):
    store = make_store(data_dir)
    guard = OfflineGuard(SyncClock(LocalDb(data_dir)), store, Bus(), 7)
    guard.start()
    assert guard.simulate(6.9) == MODE_CACHED
    assert guard.simulate(0.1) == MODE_DEFAULT
