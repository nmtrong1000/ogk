from datetime import date, timedelta

import pytest

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.seed import EVENT_DAYS, PARENT1_EMAIL, seed
from tests.conftest import login
from tests.reports.conftest import NOW, two_children_device
from tests.sync.conftest import event, heartbeat_body, post_events, send_heartbeat

pytestmark = pytest.mark.anyio

SEED_PASSWORD = "mat-khau-seed-1"
TODAY = date(2026, 11, 19)


async def seeded_children(client) -> dict[str, dict]:
    async with get_sessionmaker()() as db:
        await seed(db, SEED_PASSWORD, NOW)
    assert (await login(client, PARENT1_EMAIL, SEED_PASSWORD)).status_code == 200
    return {c["name"]: c for c in (await client.get("/api/children")).json()}


def expected_seconds(day: int, offset: int) -> int:
    return 3000 + 600 * ((day + offset) % 3)


async def test_report_matches_seed_data(app, client, frozen):
    children = await seeded_children(client)
    start, end = TODAY - timedelta(days=EVENT_DAYS), TODAY - timedelta(days=1)
    response = await client.get(f"/api/children/{children['An']['id']}/reports?from={start}&to={end}")
    assert response.status_code == 200, response.text
    body = response.json()
    expected_daily = [
        {"date": (TODAY - timedelta(days=day)).isoformat(), "seconds": expected_seconds(day, 0)}
        for day in range(EVENT_DAYS, 0, -1)
    ]
    assert body["daily"] == expected_daily
    assert body["total_seconds"] == sum(item["seconds"] for item in expected_daily)
    assert sum(week["seconds"] for week in body["weekly"]) == body["total_seconds"]
    assert all(date.fromisoformat(week["week_start"]).weekday() == 0 for week in body["weekly"])
    assert body["top_apps"] == [{"name": "chrome.exe", "seconds": 3000 * EVENT_DAYS}]
    assert body["top_domains"] == [
        {"domain": "wikipedia.org", "count": EVENT_DAYS},
        {"domain": "youtube.com", "count": EVENT_DAYS},
    ]
    blocked_apps = sum(1 for day in range(1, EVENT_DAYS + 1) if day % 3 == 0)
    blocked_domains = sum(1 for day in range(1, EVENT_DAYS + 1) if day % 2 == 1)
    total = blocked_apps + blocked_domains
    assert body["blocked"] == {"apps": blocked_apps, "domains": blocked_domains, "total": total}
    assert body["quota_today_seconds"] == 120 * 60
    assert (body["from"], body["to"], body["time_zone"]) == (str(start), str(end), get_settings().report_tz)

    binh = (await client.get(f"/api/children/{children['Bình']['id']}/reports?from={start}&to={end}")).json()
    assert [d["seconds"] for d in binh["daily"]] == [expected_seconds(day, 1) for day in range(EVENT_DAYS, 0, -1)]
    assert binh["blocked"]["total"] == 0


async def test_default_range_is_last_seven_days_ending_today(app, client, frozen):
    children = await seeded_children(client)
    body = (await client.get(f"/api/children/{children['An']['id']}/reports")).json()
    assert body["to"] == str(TODAY)
    assert body["from"] == str(TODAY - timedelta(days=6))
    assert body["daily"][-1] == {"date": str(TODAY), "seconds": 0}


async def test_days_counts_back_from_today(app, client, frozen):
    children = await seeded_children(client)
    body = (await client.get(f"/api/children/{children['An']['id']}/reports?days=30")).json()
    assert (body["from"], body["to"], len(body["daily"])) == (str(TODAY - timedelta(days=29)), str(TODAY), 30)
    assert body["total_seconds"] == sum(expected_seconds(day, 0) for day in range(1, EVENT_DAYS + 1))


async def test_invalid_range_is_rejected(app, client, frozen):
    children = await seeded_children(client)
    url = f"/api/children/{children['An']['id']}/reports"
    assert (await client.get(f"{url}?from=2026-11-19&to=2026-11-18")).json()["detail"] == "invalid_range"
    assert (await client.get(f"{url}?from=2026-01-01&to=2026-11-18")).status_code == 422
    assert (await client.get(f"{url}?days=91")).json()["detail"] == "invalid_range"
    assert (await client.get(f"{url}?days=0")).json()["detail"] == "invalid_range"


async def test_events_are_cut_by_report_time_zone(parent, agent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    device_id, token = tokens["device_id"], tokens["access_token"]
    late = event(device_id, an["id"], type="app_stop", subject="late.exe", duration_sec=60, ts="2026-11-18T16:59:00Z")
    early = event(device_id, an["id"], type="app_stop", subject="early.exe", duration_sec=60, ts="2026-11-18T17:01:00Z")
    assert (await post_events(agent, token, [late, early])).status_code == 200
    day18 = (await parent.get(f"/api/children/{an['id']}/reports?from=2026-11-18&to=2026-11-18")).json()
    day19 = (await parent.get(f"/api/children/{an['id']}/reports?from=2026-11-19&to=2026-11-19")).json()
    assert [a["name"] for a in day18["top_apps"]] == ["late.exe"]
    assert [a["name"] for a in day19["top_apps"]] == ["early.exe"]


async def test_top_lists_stop_at_ten(parent, agent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    events = [
        event(tokens["device_id"], an["id"], type="app_stop", subject=f"app{i:02}.exe", duration_sec=100 + i)
        for i in range(12)
    ]
    events += [
        event(tokens["device_id"], an["id"], type="domain_query", subject=f"site{i:02}.vn", duration_sec=0)
        for i in range(12)
    ]
    await post_events(agent, tokens["access_token"], [{**e, "ts": "2026-11-19T01:00:00Z"} for e in events])
    body = (await parent.get(f"/api/children/{an['id']}/reports?from=2026-11-19&to=2026-11-19")).json()
    assert [a["name"] for a in body["top_apps"]] == [f"app{i:02}.exe" for i in range(11, 1, -1)]
    assert len(body["top_domains"]) == 10


async def test_usage_from_several_devices_is_summed(parent, agent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    second, _, _ = await two_children_device(parent, agent)
    usage = [{"child_id": an["id"], "day": "2026-11-19", "seconds": 600}]
    for t in (tokens, second):
        response = await send_heartbeat(agent, t["access_token"], {**heartbeat_body(), "usage_days": usage})
        assert response.status_code == 200
    body = (await parent.get(f"/api/children/{an['id']}/reports?from=2026-11-19&to=2026-11-19")).json()
    assert body["daily"] == [{"date": "2026-11-19", "seconds": 1200}]


async def test_other_parent_cannot_read_report(parent, agent, other_parent, frozen):
    _, an, _ = await two_children_device(parent, agent)
    assert (await other_parent.get(f"/api/children/{an['id']}/reports")).status_code == 404
    assert (await other_parent.get(f"/api/children/{an['id']}/reports/requests")).status_code == 404


async def test_requests_are_paginated_per_child(parent, agent, frozen):
    tokens, an, binh = await two_children_device(parent, agent)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    for _ in range(3):
        await agent.post("/api/device/requests", json={"child_id": an["id"], "type": "add_time"}, headers=headers)
    await agent.post("/api/device/requests", json={"child_id": binh["id"], "type": "add_time"}, headers=headers)
    first = (await parent.get(f"/api/children/{an['id']}/reports/requests?page=1&size=2")).json()
    second = (await parent.get(f"/api/children/{an['id']}/reports/requests?page=2&size=2")).json()
    assert (first["total"], len(first["items"]), len(second["items"])) == (3, 2, 1)
    assert {item["child_id"] for item in first["items"] + second["items"]} == {an["id"]}
    assert first["items"][0]["child_name"] == "An"
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == sorted(ids, reverse=True)
    assert (await parent.get(f"/api/children/{an['id']}/reports/requests?size=101")).status_code == 422


async def test_admin_cannot_read_reports(parent, agent, admin, frozen):
    _, an, _ = await two_children_device(parent, agent)
    assert (await admin.get(f"/api/children/{an['id']}/reports")).status_code == 403
