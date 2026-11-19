import pytest

from app.modules.sync.models import Event, EventBatch
from tests.enrollment.conftest import bearer
from tests.family.conftest import create_child
from tests.sync.conftest import EVENT_VECTORS, count, event, mapped_device, post_events

pytestmark = pytest.mark.anyio


async def test_accepts_batch(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    events = [event(tokens["device_id"], child["id"]), event(tokens["device_id"], child["id"], type="app_stop")]
    response = await post_events(agent, tokens["access_token"], events)
    assert response.status_code == 200
    assert response.json() == {"accepted": 2, "duplicate": False}
    assert await count(Event) == 2


async def test_resent_batch_not_stored_twice(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    events = [event(tokens["device_id"], child["id"])]
    await post_events(agent, tokens["access_token"], events, key="k1")
    response = await post_events(agent, tokens["access_token"], events, key="k1")
    assert response.json() == {"accepted": 0, "duplicate": True}
    assert await count(Event) == 1
    assert await count(EventBatch) == 1
    assert (await post_events(agent, tokens["access_token"], events, key="k2")).json()["accepted"] == 1
    assert await count(Event) == 2


async def test_key_is_scoped_per_device(parent, agent):
    pc1, child = await mapped_device(parent, agent, name="PC1")
    pc2, _ = await mapped_device(parent, agent, name="PC2")
    await post_events(agent, pc1["access_token"], [event(pc1["device_id"], child["id"])], key="same")
    response = await post_events(agent, pc2["access_token"], [event(pc2["device_id"], child["id"])], key="same")
    assert response.json() == {"accepted": 1, "duplicate": False}


@pytest.mark.parametrize("key", [None, "", "a" * 65, "has space", "a.b"])
async def test_rejects_missing_or_malformed_key(parent, agent, key):
    tokens, child = await mapped_device(parent, agent)
    response = await post_events(agent, tokens["access_token"], [event(tokens["device_id"], child["id"])], key=key)
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_idempotency_key"


@pytest.mark.parametrize("case", EVENT_VECTORS["invalid"], ids=lambda c: c["name"])
async def test_rejects_invalid_vector(parent, agent, case):
    tokens, child = await mapped_device(parent, agent)
    bad = {**case["event"]}
    if "device_id" in bad:
        bad["device_id"] = tokens["device_id"]
    if "child_id" in bad:
        bad["child_id"] = child["id"]
    good = event(tokens["device_id"], child["id"])
    response = await post_events(agent, tokens["access_token"], [good, bad])
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_event", "index": 1, "field": case["field"]}
    assert await count(Event) == 0
    assert await count(EventBatch) == 0


async def test_rejects_other_device_id(parent, agent):
    tokens, child = await mapped_device(parent, agent)
    response = await post_events(agent, tokens["access_token"], [event(tokens["device_id"] + 1, child["id"])])
    assert response.json()["field"] == "device_id"


async def test_rejects_child_of_other_parent(parent, agent, other_parent):
    tokens, _ = await mapped_device(parent, agent)
    foreign = (await create_child(other_parent, "Lạ")).json()
    response = await post_events(agent, tokens["access_token"], [event(tokens["device_id"], foreign["id"])])
    assert response.json()["field"] == "child_id"


async def test_accepts_owned_child_not_mapped_to_device(parent, agent):
    tokens, _ = await mapped_device(parent, agent)
    other = (await create_child(parent, "Bình")).json()
    response = await post_events(agent, tokens["access_token"], [event(tokens["device_id"], other["id"])])
    assert response.json()["accepted"] == 1


@pytest.mark.parametrize(
    "payload", [[], {"events": []}, {"events": "x"}, {"events": [{}], "extra": 1}, {"events": [{}] * 501}]
)
async def test_rejects_malformed_batch(parent, agent, payload):
    tokens, _ = await mapped_device(parent, agent)
    headers = {**bearer(tokens["access_token"]), "Idempotency-Key": "k"}
    response = await agent.post("/api/device/events", json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_batch"


async def test_rejects_non_json_body(parent, agent):
    tokens, _ = await mapped_device(parent, agent)
    headers = {**bearer(tokens["access_token"]), "Idempotency-Key": "k", "Content-Type": "application/json"}
    response = await agent.post("/api/device/events", content=b"{not json", headers=headers)
    assert response.json()["detail"] == "invalid_batch"


async def test_requires_device_token(parent, agent):
    assert (await post_events(agent, "wrong", [])).json()["detail"] == "invalid_token"
