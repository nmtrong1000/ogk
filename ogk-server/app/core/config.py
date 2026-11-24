from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, ValidationError, field_validator
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
    policy_signing_key: Path | None = None
    seed_password: SecretStr | None = None
    report_tz: str = "Asia/Ho_Chi_Minh"

    @field_validator("report_tz")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown time zone") from None
        return value

    @property
    def report_zone(self) -> ZoneInfo:
        return ZoneInfo(self.report_tz)

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
