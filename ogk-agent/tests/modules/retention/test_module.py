import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from service.core.bus import Bus
from service.core.commands import CommandState
from service.core.local_db import CHILD_COUNTER, DB_FILE, LocalDb
from service.core.request_state import RequestState
from service.modules.retention import PURGE_COMMANDS, RetentionModule
from service.modules.sync import SyncModule
from tests.modules.screentime.test_module import Rig as ScreenRig
from tests.modules.sync.test_heartbeat import Rig as SyncRig

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 24, 5, 0, tzinfo=UTC)


def event(child_id: int) -> str:
    return json.dumps({"child_id": child_id, "type": "app_start"})


def rows(data_dir, sql: str) -> list[tuple]:
    with sqlite3.connect(data_dir / DB_FILE) as conn:
        return conn.execute(sql).fetchall()


def day(age: int) -> str:
    return (NOW.date() - timedelta(days=age)).isoformat()


async def test_purge_expired_removes_only_data_older_than_90_days(data_dir):
    db = LocalDb(data_dir)
    for age in (91, 89):
        at = NOW - timedelta(days=age)
        db.save_usage(day(age), {(7, CHILD_COUNTER): 60.0}, at)
        db.add_events([event(7)], at)
        db.save_command_receipt(age, at)
    module = RetentionModule(db, Bus(), now=lambda: NOW, local_now=lambda: NOW)

    counts = await module.purge_expired()

    assert counts == {"usage": 1, "event_outbox": 1, "command_receipts": 1}
    assert rows(data_dir, "SELECT day FROM usage") == [(day(89),)]
    assert len(rows(data_dir, "SELECT id FROM event_outbox")) == 1
    assert rows(data_dir, "SELECT command_id FROM command_receipts") == [(89,)]


async def test_purge_child_removes_only_that_childs_local_data(data_dir):
    db = LocalDb(data_dir)
    db.save_usage(day(1), {(7, CHILD_COUNTER): 60.0, (8, CHILD_COUNTER): 30.0}, NOW)
    db.save_command_state(7, day(0), day(0), 900)
    db.save_command_state(8, day(0), None, 0)
    db.add_events([event(7), event(8), event(7)], NOW)
    requests = RequestState()
    requests.update([{"id": 1, "child_id": 7}, {"id": 2, "child_id": 8}])
    module = RetentionModule(db, Bus(), now=lambda: NOW, requests=requests)

    await module.execute_command({"id": 5, "child_id": 7, "type": "purge_child", "minutes": 0})

    assert rows(data_dir, "SELECT child_id FROM usage") == [(8,)]
    assert rows(data_dir, "SELECT child_id FROM command_state") == [(8,)]
    payloads = [json.loads(p) for (p,) in rows(data_dir, "SELECT payload FROM event_outbox")]
    assert [p["child_id"] for p in payloads] == [8]
    assert [item["id"] for item in requests.snapshot()["results"]] == [2]


async def test_screen_time_does_not_write_purged_usage_back(data_dir):
    rig = ScreenRig(data_dir)
    rig.module._db = rig.db
    rig.policy()
    await rig.start()
    await rig.run(60)
    assert rig.db.load_usage(rig.module._counters.day)[(7, CHILD_COUNTER)] >= 60
    module = RetentionModule(rig.db, rig.bus, now=lambda: rig.wall)

    await module.execute_command({"id": 5, "child_id": 7, "type": "purge_child", "minutes": 0})
    assert rig.screen.used_today.get(7, 0) == 0
    await rig.run(31)

    assert rig.db.load_usage(rig.module._counters.day)[(7, CHILD_COUNTER)] <= 31
    assert rows(data_dir, "SELECT * FROM command_state") == []


async def test_purge_unlocks_quota_lock_and_rechecks_policy(data_dir):
    rig = ScreenRig(data_dir)
    rig.module._db = rig.db
    rig.policy(quota=1, schedule=["1" * 48] * 7)
    await rig.start()
    await rig.run(120)
    assert rig.screen.state == "locked"
    assert rig.screen.lock_reason == "quota"

    retention = RetentionModule(rig.db, rig.bus, now=lambda: rig.wall)
    await retention.execute_command({"id": 6, "child_id": 7, "type": "purge_child", "minutes": 0})
    await rig.module.tick()

    assert rig.screen.state == "ok"
    assert rig.screen.lock_reason is None
    assert rig.screen.remaining_seconds == 60
    assert rig.screen.used_seconds == 0


async def test_purge_does_not_clear_schedule_lock(data_dir):
    rig = ScreenRig(data_dir)
    rig.module._db = rig.db
    rig.policy(schedule=["0" * 48] * 7)
    await rig.start()
    assert rig.screen.state == "locked"
    assert rig.screen.lock_reason == "schedule"

    retention = RetentionModule(rig.db, rig.bus, now=lambda: rig.wall)
    await retention.execute_command({"id": 7, "child_id": 7, "type": "purge_child", "minutes": 0})
    await rig.module.tick()

    assert rig.screen.state == "locked"
    assert rig.screen.lock_reason == "schedule"


async def test_purge_command_from_heartbeat_wipes_child_then_acknowledges(data_dir):
    rig = SyncRig(data_dir)
    rig.db.save_usage(day(0), {(7, CHILD_COUNTER): 60.0}, NOW)
    commands = CommandState(rig.db)
    retention = RetentionModule(rig.db, rig.bus, now=lambda: rig.server.now)
    commands.register(PURGE_COMMANDS, retention.execute_command)
    sync = SyncModule(
        rig.session,
        rig.queue,
        rig.offline,
        rig.store,
        rig.enforcement,
        rig.bus,
        interval=0.01,
        screen=rig.screen,
        alerts=rig.alerts,
        commands=commands,
    )
    rig.server.commands = [{"id": 41, "child_id": 7, "type": "purge_child", "minutes": 0}]

    assert await sync.tick()

    assert rig.server.acked == [41]
    assert rows(data_dir, "SELECT * FROM usage") == []
    assert rows(data_dir, "SELECT command_id FROM command_receipts") == [(41,)]
