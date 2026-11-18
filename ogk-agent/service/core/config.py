import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE = "config.json"
DEFAULT_POLICY_PUBLIC_KEY = "policy_public.pem"
DEFAULT_IPC_PORT = 47800


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    server_url: str
    ca_cert: Path
    health_interval: float = 30.0
    ipc_port: int = DEFAULT_IPC_PORT
    policy_public_key: Path | None = None


def load_config(data_dir: Path) -> Config:
    path = data_dir / CONFIG_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}") from None
    except json.JSONDecodeError:
        raise ConfigError(f"Config file is not valid JSON: {path}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"Config file must be a JSON object: {path}")

    bad = []
    server_url = raw.get("server_url")
    if not isinstance(server_url, str) or not server_url.startswith("https://"):
        bad.append("server_url")
    ca_cert = raw.get("ca_cert")
    if not isinstance(ca_cert, str) or not ca_cert:
        bad.append("ca_cert")
    interval = raw.get("health_interval", 30)
    if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0:
        bad.append("health_interval")
    ipc_port = raw.get("ipc_port", DEFAULT_IPC_PORT)
    if isinstance(ipc_port, bool) or not isinstance(ipc_port, int) or not 1 <= ipc_port <= 65535:
        bad.append("ipc_port")
    policy_public_key = raw.get("policy_public_key", DEFAULT_POLICY_PUBLIC_KEY)
    if not isinstance(policy_public_key, str) or not policy_public_key:
        bad.append("policy_public_key")
    if bad:
        raise ConfigError(f"Missing or invalid config fields: {', '.join(bad)}")

    return Config(
        server_url=server_url.rstrip("/"),
        ca_cert=data_dir / ca_cert,
        health_interval=float(interval),
        ipc_port=ipc_port,
        policy_public_key=data_dir / policy_public_key,
    )
