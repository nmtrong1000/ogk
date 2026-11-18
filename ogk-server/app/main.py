from fastapi import FastAPI

from app.core import dashboard, errors, health
from app.core.config import get_settings
from app.core.security import CSRFMiddleware, RateLimiter
from app.modules.auth.router import admin_router as auth_admin_router
from app.modules.auth.router import router as auth_router
from app.modules.family.router import router as family_router

# Đường dùng token thiết bị thay cho cookie, không cần CSRF (P8 thêm).
CSRF_EXEMPT_PREFIXES: tuple[str, ...] = ()


def create_app() -> FastAPI:
    app = FastAPI(title="OGK-Server")
    app.state.rate_limiter = RateLimiter()
    errors.register(app)
    app.add_middleware(CSRFMiddleware, exempt_prefixes=CSRF_EXEMPT_PREFIXES)
    app.include_router(health.router)
    app.include_router(auth_router)
    app.include_router(auth_admin_router)
    app.include_router(family_router)
    dist = get_settings().dashboard_dist
    if dist and (dist / "index.html").is_file():
        dashboard.register(app, dist)
    return app
