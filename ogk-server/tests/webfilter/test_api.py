import pytest

from tests.conftest import create_admin, csrf_headers, make_client
from tests.family.conftest import create_child

pytestmark = pytest.mark.anyio


async def test_parent_updates_domain_rules_and_allowlist_wins(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.patch(
        f"/api/children/{child['id']}/policy",
        json={"web_blocklist": ["Example.com."], "web_allowlist": ["school.edu.vn"], "blocked_categories": ["adult"]},
        headers=await csrf_headers(parent),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["web_blocklist"] == ["example.com"]
    assert body["web_allowlist"] == ["school.edu.vn"]
    assert body["blocked_categories"] == ["adult"]


async def test_invalid_domain_rules_rejected(parent):
    child = (await create_child(parent, "An")).json()
    response = await parent.patch(
        f"/api/children/{child['id']}/policy",
        json={"web_blocklist": ["https://example.com/path"]},
        headers=await csrf_headers(parent),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_domain_rules"


async def test_catalog_is_admin_only_and_audited(app, parent):
    child = (await create_child(parent, "An")).json()
    assert len((await parent.get(f"/api/children/{child['id']}/webfilter/categories")).json()["categories"]) == 6
    assert (await parent.get("/api/admin/webfilter/catalog")).status_code == 403
    await create_admin()
    async with make_client(app) as admin:
        from tests.conftest import login

        await login(admin, "admin@ogk.local")
        response = await admin.get("/api/admin/webfilter/catalog")
        assert response.status_code == 200
        assert len(response.json()) >= 200
        changed = await admin.put(
            "/api/admin/webfilter/catalog/example.org",
            json={"category": "education"},
            headers=await csrf_headers(admin),
        )
        assert changed.status_code == 200
        assert changed.json()["category"] == "education"


async def test_parent_cannot_read_categories_for_another_child(parent, app):
    from tests.conftest import make_client, register

    async with make_client(app) as other:
        await register(other, "other@example.com")
        child = (await create_child(other, "Other")).json()
    assert (await parent.get(f"/api/children/{child['id']}/webfilter/categories")).status_code == 404
