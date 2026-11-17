from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import (
    SESSION_COOKIE,
    clear_session_cookie,
    rate_limit,
    set_csrf_cookie,
    set_session_cookie,
)
from app.modules.auth import service
from app.modules.auth.models import Account
from app.modules.auth.schemas import AccountOut, AdminAccountOut, Credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(service.require_admin)])


async def _start_session(request: Request, response: Response, db: AsyncSession, account: Account) -> None:
    old = request.cookies.get(SESSION_COOKIE)
    if old:
        await service.delete_session(db, old)
    set_session_cookie(response, await service.create_session(db, account))
    set_csrf_cookie(response)


@router.post("/register", status_code=201, response_model=AccountOut, dependencies=[rate_limit("register", 5)])
async def register(body: Credentials, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    account = await service.create_account(db, body.email, body.password)
    await _start_session(request, response, db, account)
    return account


@router.post("/login", response_model=AccountOut, dependencies=[rate_limit("login", 10)])
async def login(body: Credentials, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    account = await service.authenticate(db, body.email, body.password)
    await _start_session(request, response, db, account)
    return account


@router.post("/logout", status_code=204)
async def logout(
    request: Request, _account: Account = Depends(service.current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    await service.delete_session(db, request.cookies[SESSION_COOKIE])
    response = Response(status_code=204)
    clear_session_cookie(response)
    set_csrf_cookie(response)
    return response


@router.get("/me", response_model=AccountOut)
async def me(account: Account = Depends(service.current_user)):
    return account


@admin_router.get("/accounts", response_model=list[AdminAccountOut])
async def list_accounts(locked: bool = False, db: AsyncSession = Depends(get_db)):
    return await service.list_parent_accounts(db, locked_only=locked)


@admin_router.post("/accounts/{account_id}/unlock", response_model=AdminAccountOut)
async def unlock_account(account_id: int, db: AsyncSession = Depends(get_db)):
    return await service.unlock_parent(db, account_id)
