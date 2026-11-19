import pytest

from tests.conftest import csrf_headers
from tests.sync.conftest import heartbeat_body, mapped_device, send_heartbeat

pytestmark = pytest.mark.anyio

DISABLED = {"type": "enforcement_disabled", "detail": "tray_unavailable", "ts": "2026-11-19T08:00:00Z"}


async def raise_alert(agent, tokens: dict) -> None:
    response = await send_heartbeat(agent, tokens["access_token"], heartbeat_body(alerts=[DISABLED]))
    assert response.status_code == 200


async def test_lists_alerts_with_device_name(parent, agent):
    tokens, _ = await mapped_device(parent, agent, name="PC phòng khách")
    await raise_alert(agent, tokens)
    (alert,) = (await parent.get("/api/alerts")).json()
    assert alert["device_id"] == tokens["device_id"]
    assert alert["device_name"] == "PC phòng khách"


async def test_filters_by_device(parent, agent):
    pc1, _ = await mapped_device(parent, agent, name="PC1")
    pc2, _ = await mapped_device(parent, agent, name="PC2")
    await raise_alert(agent, pc1)
    await raise_alert(agent, pc2)
    assert len((await parent.get("/api/alerts")).json()) == 2
    alerts = (await parent.get("/api/alerts", params={"device_id": pc2["device_id"]})).json()
    assert [a["device_id"] for a in alerts] == [pc2["device_id"]]


async def test_other_parent_sees_nothing(parent, agent, other_parent):
    tokens, _ = await mapped_device(parent, agent)
    await raise_alert(agent, tokens)
    assert (await other_parent.get("/api/alerts")).json() == []
    response = await other_parent.get("/api/alerts", params={"device_id": tokens["device_id"]})
    assert response.status_code == 404
    assert response.json()["detail"] == "not_found"


async def test_removed_device_hidden(parent, agent):
    tokens, _ = await mapped_device(parent, agent)
    await raise_alert(agent, tokens)
    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert (await parent.get("/api/alerts")).json() == []


async def test_requires_parent(client, admin):
    assert (await client.get("/api/alerts")).json()["detail"] == "not_authenticated"
    assert (await admin.get("/api/alerts")).json()["detail"] == "forbidden"
