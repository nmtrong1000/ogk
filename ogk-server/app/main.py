import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
from app.modules.reports.router import child_view_router as reports_child_view_router
from app.modules.reports.router import device_router as reports_device_router
from app.modules.reports.router import router as reports_router
from app.modules.retention import service as retention
from app.modules.retention.router import router as retention_router
from app.modules.sync.router import command_router as sync_command_router
from app.modules.sync.router import device_router as sync_device_router
from app.modules.sync.router import request_router as sync_request_router
from app.modules.sync.router import router as sync_router
from app.modules.webfilter.router import admin_router as webfilter_admin_router
from app.modules.webfilter.router import parent_router as webfilter_parent_router

CSRF_EXEMPT_PREFIXES: tuple[str, ...] = DEVICE_PREFIXES


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(retention.run_daily())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    app = FastAPI(title="OGK-Server", lifespan=lifespan)
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
    app.include_router(reports_router)
    app.include_router(reports_device_router)
    app.include_router(reports_child_view_router)
    app.include_router(retention_router)
    dist = get_settings().dashboard_dist
    if dist and (dist / "index.html").is_file():
        dashboard.register(app, dist)
    return app
