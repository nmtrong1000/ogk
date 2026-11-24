from datetime import timedelta

import httpx
import pytest

from app.modules.reports.router import CHILD_VIEW_COOKIE
from tests.conftest import csrf_headers, make_client
from tests.enrollment.conftest import bearer
from tests.policy.conftest import patch_policy
from tests.reports.conftest import CODE, register_code, two_children_device
from tests.sync.conftest import heartbeat_body, send_heartbeat

pytestmark = pytest.mark.anyio


@pytest.fixture
async def browser(app):
    async with make_client(app) as c:
        yield c


async def open_session(browser: httpx.AsyncClient, code: str = CODE) -> httpx.Response:
    return await browser.post("/api/child-view/session", json={"code": code}, headers=await csrf_headers(browser))


async def test_code_opens_session_for_that_child_only(parent, agent, browser, frozen):
    tokens, an, binh = await two_children_device(parent, agent)
    token = tokens["access_token"]
    await patch_policy(parent, an["id"], weekday_quota_minutes=90)
    await patch_policy(parent, binh["id"], weekday_quota_minutes=30)
    usage = [
        {"child_id": an["id"], "day": "2026-11-19", "seconds": 1200},
        {"child_id": binh["id"], "day": "2026-11-19", "seconds": 300},
    ]
    await send_heartbeat(agent, token, {**heartbeat_body(), "usage_days": usage})
    created = await register_code(agent, token, an["id"])
    assert created.status_code == 201, created.text
    response = await open_session(browser)
    assert response.status_code == 204
    cookie = next(c for c in browser.cookies.jar if c.name == CHILD_VIEW_COOKIE)
    assert cookie.path == "/api/child-view"
    assert (await browser.get("/api/child-view/me")).json() == {"name": "An"}
    today = (await browser.get("/api/child-view/today")).json()
    assert today["child_id"] == an["id"]
    assert today["daily"] == [{"date": "2026-11-19", "seconds": 1200}]
    assert today["quota_today_seconds"] == 90 * 60
    log = (await browser.get("/api/child-view/rule-log")).json()
    assert log["total"] == 1
    assert log["items"][0]["changes"] == {"weekday_quota_minutes": {"old": 120, "new": 90}}
    assert set(log["items"][0]) == {"id", "at", "changes"}


async def test_child_view_is_the_same_report_the_parent_sees(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    await open_session(browser)
    child = (await browser.get("/api/child-view/today")).json()
    parent_view = (await parent.get(f"/api/children/{an['id']}/reports?from=2026-11-19&to=2026-11-19")).json()
    assert child == parent_view


async def test_used_code_is_rejected(app, parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    assert (await open_session(browser)).status_code == 204
    async with make_client(app) as other:
        again = await open_session(other)
    assert (again.status_code, again.json()["detail"]) == (400, "invalid_code")


async def test_expired_code_is_rejected(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    frozen["at"] += timedelta(seconds=61)
    response = await open_session(browser)
    assert (response.status_code, response.json()["detail"]) == (400, "invalid_code")


async def test_unknown_code_is_rejected(app, browser):
    response = await open_session(browser, "x" * 43)
    assert (response.status_code, response.json()["detail"]) == (400, "invalid_code")


async def test_session_expires(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    await open_session(browser)
    frozen["at"] += timedelta(minutes=31)
    assert (await browser.get("/api/child-view/today")).status_code == 401


async def test_session_needs_csrf(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    response = await browser.post("/api/child-view/session", json={"code": CODE})
    assert response.status_code == 403


async def test_child_view_routes_need_session(app, browser):
    for path in ("/api/child-view/me", "/api/child-view/today", "/api/child-view/rule-log"):
        assert (await browser.get(path)).status_code == 401


async def test_parent_session_does_not_open_child_view(parent, agent, frozen):
    await two_children_device(parent, agent)
    assert (await parent.get("/api/child-view/today")).status_code == 401


async def test_logout_ends_session(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    await open_session(browser)
    assert (await browser.post("/api/child-view/logout", headers=await csrf_headers(browser))).status_code == 204
    assert (await browser.get("/api/child-view/today")).status_code == 401


async def test_device_cannot_issue_code_for_unassigned_or_foreign_child(parent, agent, other_parent, frozen):
    tokens, _, _ = await two_children_device(parent, agent)
    stranger = (
        await other_parent.post(
            "/api/children", json={"name": "Lạ", "birth_year": 2015}, headers=await csrf_headers(other_parent)
        )
    ).json()
    own_unassigned = (
        await parent.post("/api/children", json={"name": "Chi", "birth_year": 2015}, headers=await csrf_headers(parent))
    ).json()
    for child_id in (stranger["id"], own_unassigned["id"], 999999):
        assert (await register_code(agent, tokens["access_token"], child_id)).status_code == 404


async def test_code_must_be_long_and_url_safe(parent, agent, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    for code in ("short", "a" * 31, "a" * 40 + "/"):
        assert (await register_code(agent, tokens["access_token"], an["id"], code)).status_code == 422


async def test_code_needs_device_token(parent, agent, frozen):
    _, an, _ = await two_children_device(parent, agent)
    response = await agent.post("/api/device/child-view-codes", json={"child_id": an["id"], "code": CODE})
    assert response.status_code == 401
    response = await agent.post(
        "/api/device/child-view-codes", json={"child_id": an["id"], "code": CODE}, headers=bearer("nope")
    )
    assert response.status_code == 401


async def test_revoked_device_code_is_rejected(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    removed = await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert removed.status_code in (200, 204)
    assert (await open_session(browser)).status_code == 400


async def test_removing_device_ends_open_session(parent, agent, browser, frozen):
    tokens, an, _ = await two_children_device(parent, agent)
    await register_code(agent, tokens["access_token"], an["id"])
    await open_session(browser)
    assert (await browser.get("/api/child-view/today")).status_code == 200
    await parent.delete(f"/api/devices/{tokens['device_id']}", headers=await csrf_headers(parent))
    assert (await browser.get("/api/child-view/today")).status_code == 401
