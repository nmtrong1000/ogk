import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.audit.models import AuditLog
from app.modules.family.models import Child, WindowsAccount
from app.modules.policy.models import Policy, PolicyVersion
from app.modules.reports.models import ChildViewSession
from app.modules.sync.models import ChildRequest, DailyUsage, Event, ParentCommand
from tests.conftest import csrf_headers
from tests.policy.conftest import set_quota
from tests.retention.conftest import NOW, seed_history
from tests.retention.test_purge import parent_id
from tests.sync.conftest import heartbeat_body, mapped_device, send_heartbeat

pytestmark = pytest.mark.anyio


async def wipe(c, child_id: int):
    return await c.delete(f"/api/children/{child_id}/data", headers=await csrf_headers(c))


async def rows(model, child_id: int) -> list:
    async with get_sessionmaker()() as db:
        return list((await db.execute(select(model).where(model.child_id == child_id))).scalars())


async def test_wipe_deletes_history_keeps_profile_and_queues_purge(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    other_tokens, other = await mapped_device(parent, agent, name="PC2")
    actor_id = await parent_id()
    await seed_history(tokens["device_id"], child["id"], actor_id, 3, "a")
    await seed_history(other_tokens["device_id"], other["id"], actor_id, 3, "b")
    assert (await set_quota(parent, child["id"], 90)).status_code == 200
    assert (await set_quota(parent, child["id"], 60)).status_code == 200
    async with get_sessionmaker()() as db:
        db.add(
            ChildViewSession(
                id="s" * 64, child_id=child["id"], device_id=tokens["device_id"], created_at=NOW, expires_at=NOW
            )
        )
        await db.commit()

    response = await wipe(parent, child["id"])

    assert response.status_code == 200
    assert response.json() == {"devices_notified": 1}
    for model in (Event, ChildRequest, DailyUsage, ChildViewSession):
        assert await rows(model, child["id"]) == [], model.__tablename__
        if model is not ChildViewSession:
            assert len(await rows(model, other["id"])) == 1
    commands = await rows(ParentCommand, child["id"])
    assert [(c.type, c.status, c.device_id) for c in commands] == [("purge_child", "pending", tokens["device_id"])]
    policy = (await rows(Policy, child["id"]))[0]
    assert [v.version for v in await rows(PolicyVersion, child["id"])] == [policy.version]
    assert policy.weekday_quota_minutes == 60
    assert len(await rows(WindowsAccount, child["id"])) == 1
    async with get_sessionmaker()() as db:
        assert await db.get(Child, child["id"]) is not None
        entry = (await db.execute(select(AuditLog).where(AuditLog.target_type == "child_data"))).scalar_one()
    assert (entry.action, entry.target_id) == ("delete", child["id"])

    beat = await send_heartbeat(agent, tokens["access_token"], heartbeat_body())
    assert [(c["type"], c["child_id"]) for c in beat.json()["commands"]] == [("purge_child", child["id"])]


async def test_wipe_of_other_parents_child_is_not_found(parent, agent, other_parent):
    tokens, child = await mapped_device(parent, agent)
    await seed_history(tokens["device_id"], child["id"], await parent_id(), 3, "a")

    assert (await wipe(other_parent, child["id"])).status_code == 404
    assert len(await rows(Event, child["id"])) == 1


async def test_wipe_requires_csrf(parent, agent):
    _, child = await mapped_device(parent, agent)
    assert (await parent.delete(f"/api/children/{child['id']}/data")).status_code == 403


async def test_parent_cannot_send_purge_through_command_api(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    response = await parent.post(
        f"/api/devices/{tokens['device_id']}/children/{child['id']}/commands",
        json={"type": "purge_child"},
        headers=await csrf_headers(parent),
    )
    assert response.status_code == 422
