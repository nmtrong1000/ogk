import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    log_dir = Path(local_app_data) / "OGK" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "tray.log"
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")],
        force=True,
    )
    return log_file
