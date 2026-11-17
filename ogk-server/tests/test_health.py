import pytest

from app.core.config import ConfigError, get_settings


@pytest.mark.anyio
async def test_health_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "journal_mode": "wal"}


def test_missing_tls_cert_is_reported(settings_env, monkeypatch):
    monkeypatch.delenv("OGK_TLS_CERT")
    get_settings.cache_clear()
    with pytest.raises(ConfigError, match="OGK_TLS_CERT"):
        get_settings()
