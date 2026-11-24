from fastapi import FastAPI

from app.core import dashboard, errors, health
from app.core.config import get_settings
from app.core.security import CSRFMiddleware, RateLimiter
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import admin_router as auth_admin_router
from app.modules.auth.router import router as auth_router
from app.modules.enrollment.router import DEVICE_PREFIXES
from app.modules.enrollment.router import device_router as enrollment_device_router
from app.modules.enrollment.router import router as enrollment_router
from app.modules.family.router import devices_router as family_devices_router
from app.modules.family.router import router as family_router
from app.modules.policy.router import device_router as policy_device_router
from app.modules.policy.router import router as policy_router
from app.modules.sync.router import command_router as sync_command_router
from app.modules.sync.router import device_router as sync_device_router
from app.modules.sync.router import request_router as sync_request_router
from app.modules.sync.router import router as sync_router
from app.modules.webfilter.router import admin_router as webfilter_admin_router
from app.modules.webfilter.router import parent_router as webfilter_parent_router

CSRF_EXEMPT_PREFIXES: tuple[str, ...] = DEVICE_PREFIXES


def create_app() -> FastAPI:
    app = FastAPI(title="OGK-Server")
    app.state.rate_limiter = RateLimiter()
    errors.register(app)
    app.add_middleware(CSRFMiddleware, exempt_prefixes=CSRF_EXEMPT_PREFIXES)
    app.include_router(health.router)
    app.include_router(auth_router)
    app.include_router(auth_admin_router)
    app.include_router(family_router)
    app.include_router(family_devices_router)
    app.include_router(enrollment_router)
    app.include_router(enrollment_device_router)
    app.include_router(audit_router)
    app.include_router(policy_router)
    app.include_router(policy_device_router)
    app.include_router(sync_router)
    app.include_router(sync_device_router)
    app.include_router(sync_command_router)
    app.include_router(sync_request_router)
    app.include_router(webfilter_parent_router)
    app.include_router(webfilter_admin_router)
    dist = get_settings().dashboard_dist
    if dist and (dist / "index.html").is_file():
        dashboard.register(app, dist)
    return app
