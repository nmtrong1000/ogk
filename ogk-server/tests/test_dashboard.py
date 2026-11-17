import httpx
import pytest

from app.core.config import get_settings
from app.core.db import get_engine
from app.main import create_app

INDEX = "<!doctype html><title>OGK</title>"


@pytest.fixture
async def dashboard_client(settings_env, monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX)
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("secret")
    monkeypatch.setenv("OGK_DASHBOARD_DIST", str(dist))
    get_settings.cache_clear()
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await get_engine().dispose()


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/", "/children/1"])
async def test_serves_index(dashboard_client, path):
    response = await dashboard_client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX


@pytest.mark.anyio
async def test_serves_asset(dashboard_client):
    response = await dashboard_client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log(1)"


@pytest.mark.anyio
async def test_api_not_shadowed(dashboard_client):
    response = await dashboard_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/api", "/api/khong-co"])
async def test_unknown_api_returns_404(dashboard_client, path):
    response = await dashboard_client.get(path)
    assert response.status_code == 404
    assert response.text != INDEX


@pytest.mark.anyio
async def test_no_path_traversal(dashboard_client):
    response = await dashboard_client.get("/%2e%2e/secret.txt")
    assert "secret" not in response.text


@pytest.mark.anyio
async def test_without_dashboard_dist(client):
    assert (await client.get("/")).status_code == 404
    assert (await client.get("/api/health")).status_code == 200
