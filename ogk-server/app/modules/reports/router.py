"""The child-view cookie is scoped to /api/child-view and SameSite=Strict, so it never reaches parent routes and
no other site can make the browser send it. The child id always comes from that session, never from the URL.
POST /api/child-view/session stays outside the CSRF-exempt device prefixes because it sets a cookie.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import rate_limit
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.enrollment.service import current_device
from app.modules.family.models import Device
from app.modules.reports import service
from app.modules.reports.schemas import (
    ChildProfileOut,
    ChildRequestPageOut,
    CodeIn,
    CodeOut,
    ReportOut,
    RuleLogPageOut,
    SessionIn,
)

CHILD_VIEW_COOKIE = "ogk_child_view"
CHILD_VIEW_PATH = "/api/child-view"

router = APIRouter(prefix="/api/children", tags=["reports"], dependencies=[Depends(require_parent)])
device_router = APIRouter(tags=["device"])
child_view_router = APIRouter(prefix=CHILD_VIEW_PATH, tags=["child-view"])


@router.get("/{child_id}/reports", response_model=ReportOut)
async def child_report(
    child_id: int,
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    days: int | None = None,
    account: Account = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    return await service.parent_report(db, child_id, account.id, start, end, days)


@router.get("/{child_id}/reports/requests", response_model=ChildRequestPageOut)
async def child_report_requests(
    child_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=service.MAX_PAGE_SIZE),
    account: Account = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    return await service.parent_requests(db, child_id, account.id, page, size)


@device_router.post(
    "/api/device/child-view-codes",
    status_code=201,
    response_model=CodeOut,
    dependencies=[rate_limit("child_view_code", 30)],
)
async def create_child_view_code(
    body: CodeIn, device: Device = Depends(current_device), db: AsyncSession = Depends(get_db)
):
    return await service.register_code(db, device, body.child_id, body.code)


async def current_child_view(request: Request, db: AsyncSession = Depends(get_db)) -> int:
    token = request.cookies.get(CHILD_VIEW_COOKIE)
    child_id = None if not token else await service.child_for_session(db, token)
    if child_id is None:
        raise AppError(401, "not_authenticated")
    return child_id


@child_view_router.post("/session", status_code=204, dependencies=[rate_limit("child_view_session", 10)])
async def open_session(body: SessionIn, request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    old = request.cookies.get(CHILD_VIEW_COOKIE)
    if old:
        await service.end_session(db, old)
    token = await service.exchange_code(db, body.code)
    response = Response(status_code=204)
    response.set_cookie(
        CHILD_VIEW_COOKIE,
        token,
        max_age=int(service.SESSION_TTL.total_seconds()),
        path=CHILD_VIEW_PATH,
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return response


@child_view_router.post("/logout", status_code=204)
async def close_session(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    token = request.cookies.get(CHILD_VIEW_COOKIE)
    if token:
        await service.end_session(db, token)
    response = Response(status_code=204)
    response.delete_cookie(CHILD_VIEW_COOKIE, path=CHILD_VIEW_PATH, httponly=True, secure=True, samesite="strict")
    return response


@child_view_router.get("/me", response_model=ChildProfileOut)
async def child_view_me(child_id: int = Depends(current_child_view), db: AsyncSession = Depends(get_db)):
    return await service.child_profile(db, child_id)


@child_view_router.get("/today", response_model=ReportOut)
async def child_view_today(child_id: int = Depends(current_child_view), db: AsyncSession = Depends(get_db)):
    return await service.child_today(db, child_id)


@child_view_router.get("/rule-log", response_model=RuleLogPageOut)
async def child_view_rule_log(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=service.MAX_PAGE_SIZE),
    child_id: int = Depends(current_child_view),
    db: AsyncSession = Depends(get_db),
):
    return await service.rule_log(db, child_id, page, size)
