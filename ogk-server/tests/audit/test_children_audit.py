"""Children changes write audit entries with who, when, IP, old value and new value.

ASGITransport connects from 127.0.0.1, which is both the socket IP and a default trusted proxy (like Vite).
"""

from datetime import datetime

import pytest

from tests.audit.conftest import audit_page
from tests.conftest import csrf_headers
from tests.family.conftest import birth_year, create_child

pytestmark = pytest.mark.anyio


async def test_create_logs_one_entry(parent):
    child = (await create_child(parent, "An", birth_year(8))).json()
    page = await audit_page(parent)
    assert page["total"] == 1
    entry = page["items"][0]
    assert entry["action"] == "create"
    assert (entry["target_type"], entry["target_id"]) == ("child", child["id"])
    assert entry["old_value"] is None
    assert entry["new_value"] == {"name": "An", "birth_year": birth_year(8)}


async def test_update_logs_all_five_fields(parent):
    me = (await parent.get("/api/auth/me")).json()
    child = (await create_child(parent, "An", birth_year(8))).json()
    response = await parent.patch(
        f"/api/children/{child['id']}", json={"name": "An Nhiên"}, headers=await csrf_headers(parent)
    )
    assert response.status_code == 200
    page = await audit_page(parent)
    assert page["total"] == 2
    entry = page["items"][0]
    assert entry["action"] == "update"
    assert entry["actor_id"] == me["id"]
    assert entry["actor_email"] == "parent@example.com"
    assert datetime.fromisoformat(entry["at"])
    assert entry["ip"] == "127.0.0.1"
    assert entry["old_value"] == {"name": "An"}
    assert entry["new_value"] == {"name": "An Nhiên"}


async def test_update_without_change_logs_nothing(parent):
    child = (await create_child(parent, "An", birth_year(8))).json()
    response = await parent.patch(
        f"/api/children/{child['id']}", json={"name": " An "}, headers=await csrf_headers(parent)
    )
    assert response.status_code == 200
    assert (await audit_page(parent))["total"] == 1


async def test_invalid_update_logs_nothing(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.patch(f"/api/children/{child['id']}", json={"name": ""}, headers=await csrf_headers(parent))
    assert response.status_code == 422
    assert (await audit_page(parent))["total"] == 1


async def test_delete_logs_old_value(parent):
    child = (await create_child(parent, "An", birth_year(8))).json()
    response = await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))
    assert response.status_code == 204
    entry = (await audit_page(parent))["items"][0]
    assert entry["action"] == "delete"
    assert entry["target_id"] == child["id"]
    assert entry["old_value"] == {"name": "An", "birth_year": birth_year(8)}
    assert entry["new_value"] is None


async def test_each_operation_one_entry(parent):
    child = (await create_child(parent, "An")).json()
    await parent.patch(f"/api/children/{child['id']}", json={"birth_year": birth_year(10)}, headers=await csrf_headers(parent))
    await parent.delete(f"/api/children/{child['id']}", headers=await csrf_headers(parent))
    page = await audit_page(parent)
    assert [e["action"] for e in page["items"]] == ["delete", "update", "create"]


async def test_forwarded_ip_via_trusted_proxy(parent):
    headers = {**await csrf_headers(parent), "X-Forwarded-For": "203.0.113.5"}
    response = await parent.post("/api/children", json={"name": "An", "birth_year": birth_year()}, headers=headers)
    assert response.status_code == 201
    assert (await audit_page(parent))["items"][0]["ip"] == "203.0.113.5"
