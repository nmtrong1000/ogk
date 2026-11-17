from fastapi import FastAPI

from app.core import health


def create_app() -> FastAPI:
    app = FastAPI(title="OGK-Server")
    app.include_router(health.router)
    return app
