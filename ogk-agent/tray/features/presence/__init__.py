from tray.features.presence.heartbeat import start_heartbeat
from tray.features.presence.icon import create_icon
from tray.features.presence.window import StatusWindow

STARTUP_TITLE = "OGK đã khởi động"
STARTUP_MESSAGE = "Phụ huynh đang quản lý thời gian dùng máy tính này."

__all__ = ["STARTUP_MESSAGE", "STARTUP_TITLE", "StatusWindow", "create_icon", "start_heartbeat"]
