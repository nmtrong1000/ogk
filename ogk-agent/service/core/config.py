import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILE = "config.json"
DEFAULT_IPC_PORT = 47800


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    server_url: str
    ca_cert: Path
    health_interval: float = 30.0
    ipc_port: int = DEFAULT_IPC_PORT


def load_config(data_dir: Path) -> Config:
    path = data_dir / CONFIG_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ConfigError(f"Không tìm thấy tệp cấu hình: {path}") from None
    except json.JSONDecodeError:
        raise ConfigError(f"Tệp cấu hình không phải JSON hợp lệ: {path}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"Tệp cấu hình phải là một đối tượng JSON: {path}")

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
    if bad:
        raise ConfigError(f"Thiếu hoặc sai trường cấu hình: {', '.join(bad)}")

    return Config(
        server_url=server_url.rstrip("/"),
        ca_cert=data_dir / ca_cert,
        health_interval=float(interval),
        ipc_port=ipc_port,
    )
