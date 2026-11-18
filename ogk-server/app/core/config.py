from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OGK_", env_file=".env", extra="ignore")

    database_url: str
    tls_cert: Path
    tls_key: Path
    host: str = "0.0.0.0"
    port: int = 8443
    dashboard_dist: Path | None = None
    data_key: SecretStr
    trusted_proxies: str = "127.0.0.1,::1"

    @property
    def trusted_proxy_set(self) -> frozenset[str]:
        return frozenset(p.strip() for p in self.trusted_proxies.split(",") if p.strip())


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        names = ", ".join(f"OGK_{str(err['loc'][0]).upper()}" for err in exc.errors())
        raise ConfigError(f"Missing or invalid config variables: {names}") from None
