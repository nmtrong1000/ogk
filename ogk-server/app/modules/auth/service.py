from datetime import datetime, timedelta

from fastapi import Depends, Request
from passlib.context import CryptContext
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.db import get_db, utcnow
from app.core.errors import AppError
from app.core.security import SESSION_COOKIE, SESSION_MAX_AGE, hash_token, new_token
from app.modules.auth.models import ROLE_ADMIN, ROLE_PARENT, Account, AuthSession

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)
SESSION_TTL = timedelta(seconds=SESSION_MAX_AGE)

_pwd = CryptContext(schemes=["argon2"], argon2__type="ID")
_dummy_hash: str | None = None


def now() -> datetime:
    """Đồng hồ của module; test thay hàm này để giả lập thời gian trôi."""
    return utcnow()


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    local, sep, domain = email.partition("@")
    if not sep or not local or not domain or "@" in domain or len(email) > 254 or any(c.isspace() for c in email):
        raise AppError(422, "invalid_email")
    return email


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError(422, "password_too_short")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise AppError(422, "password_too_long")


async def hash_password(password: str) -> str:
    return await run_in_threadpool(_pwd.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await run_in_threadpool(_pwd.verify, password, password_hash)


async def _verify_dummy(password: str) -> None:
    """Băm giả khi email không tồn tại để thời gian trả lời giống trường hợp sai mật khẩu."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = await hash_password(new_token())
    await verify_password(password, _dummy_hash)


def is_locked(account: Account, at: datetime | None = None) -> bool:
    return account.locked_until is not None and account.locked_until > (at or now())


async def get_by_email(db: AsyncSession, email: str) -> Account | None:
    return (await db.execute(select(Account).where(Account.email == email))).scalar_one_or_none()


async def create_account(db: AsyncSession, email: str, password: str, role: str = ROLE_PARENT) -> Account:
    email = normalize_email(email)
    validate_password(password)
    if await get_by_email(db, email) is not None:
        raise AppError(409, "email_taken")
    account = Account(
        email=email, password_hash=await hash_password(password), role=role, failed_attempts=0, created_at=now()
    )
    db.add(account)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "email_taken") from None
    return account


async def authenticate(db: AsyncSession, email: str, password: str) -> Account:
    try:
        email = normalize_email(email)
    except AppError:
        raise AppError(401, "invalid_credentials") from None
    account = await get_by_email(db, email)
    if account is None:
        await _verify_dummy(password)
        raise AppError(401, "invalid_credentials")

    at = now()
    if is_locked(account, at):
        raise AppError(423, "account_locked", locked_until=_iso(account.locked_until))

    if not await verify_password(password, account.password_hash):
        # Tăng bộ đếm bằng một câu UPDATE để các lần thử song song không đếm thiếu.
        failed = (
            await db.execute(
                update(Account)
                .where(Account.id == account.id)
                .values(failed_attempts=Account.failed_attempts + 1)
                .returning(Account.failed_attempts)
            )
        ).scalar_one()
        if failed >= MAX_FAILED_ATTEMPTS:
            locked_until = at + LOCK_DURATION
            await db.execute(
                update(Account).where(Account.id == account.id).values(failed_attempts=0, locked_until=locked_until)
            )
            await db.commit()
            raise AppError(423, "account_locked", locked_until=_iso(locked_until))
        await db.commit()
        raise AppError(401, "invalid_credentials")

    if account.failed_attempts or account.locked_until is not None:
        account.failed_attempts = 0
        account.locked_until = None
        await db.commit()
    return account


async def create_session(db: AsyncSession, account: Account) -> str:
    token = new_token()
    at = now()
    await db.execute(delete(AuthSession).where(AuthSession.expires_at <= at))
    db.add(AuthSession(id=hash_token(token), account_id=account.id, created_at=at, expires_at=at + SESSION_TTL))
    await db.commit()
    return token


async def delete_session(db: AsyncSession, token: str) -> None:
    await db.execute(delete(AuthSession).where(AuthSession.id == hash_token(token)))
    await db.commit()


async def account_for_session(db: AsyncSession, token: str) -> Account | None:
    row = (
        await db.execute(
            select(AuthSession, Account)
            .join(Account, Account.id == AuthSession.account_id)
            .where(AuthSession.id == hash_token(token))
        )
    ).one_or_none()
    if row is None:
        return None
    session, account = row
    if session.expires_at <= now():
        await db.delete(session)
        await db.commit()
        return None
    return account


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Account:
    """Dependency: tài khoản của phiên hiện tại, không có thì 401."""
    token = request.cookies.get(SESSION_COOKIE)
    account = await account_for_session(db, token) if token else None
    if account is None:
        raise AppError(401, "not_authenticated")
    return account


def require_role(*roles: str):
    """Dependency: phiên phải có một trong các vai trò, sai thì 403."""

    async def dependency(account: Account = Depends(current_user)) -> Account:
        if account.role not in roles:
            raise AppError(403, "forbidden")
        return account

    return dependency


require_parent = require_role(ROLE_PARENT)
require_admin = require_role(ROLE_ADMIN)


async def list_parent_accounts(db: AsyncSession, locked_only: bool = False) -> list[Account]:
    stmt = select(Account).where(Account.role == ROLE_PARENT).order_by(Account.email)
    if locked_only:
        stmt = stmt.where(Account.locked_until > now())
    return list((await db.execute(stmt)).scalars())


async def unlock_parent(db: AsyncSession, account_id: int) -> Account:
    account = await db.get(Account, account_id)
    if account is None or account.role != ROLE_PARENT:
        raise AppError(404, "not_found")
    account.failed_attempts = 0
    account.locked_until = None
    await db.commit()
    return account
