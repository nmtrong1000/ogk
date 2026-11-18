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
    # Khóa AES-256-GCM cho trường nhạy cảm: base64url của 32 byte (python -m app.cli gen-data-key).
    data_key: SecretStr


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        names = ", ".join(f"OGK_{str(err['loc'][0]).upper()}" for err in exc.errors())
        raise ConfigError(f"Thiếu hoặc sai biến cấu hình: {names}") from None
