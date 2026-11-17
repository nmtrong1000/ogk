from fastapi import FastAPI

from app.core import dashboard, health
from app.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="OGK-Server")
    app.include_router(health.router)
    dist = get_settings().dashboard_dist
    if dist and (dist / "index.html").is_file():
        dashboard.register(app, dist)
    return app
