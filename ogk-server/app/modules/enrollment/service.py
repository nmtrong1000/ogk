"""Pairing codes use Crockford base32 (no I, L, O, U); input is normalised so O->0 and I/L->1 still match.
An expired, used or unknown code all return invalid_code so a caller cannot probe which codes exist.
The code is claimed with a conditional UPDATE so two agents racing on one code cannot both enroll.
Consent is given by the parent when creating the code; enroll copies it into consent_records with the device id.
Refresh rotates both tokens. Presenting an already rotated refresh token revokes every token of the device,
because only a stolen copy can still hold it.
now() is the module clock; tests replace it to simulate time.
"""

import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Request
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, utcnow
from app.core.errors import AppError
from app.core.security import hash_token, new_token
from app.modules.audit import service as audit
from app.modules.enrollment.models import TOKEN_ACCESS, TOKEN_REFRESH, ConsentRecord, DeviceToken, PairingCode
from app.modules.family import service as family
from app.modules.family.models import Device

CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 8
CODE_TTL = timedelta(minutes=10)
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=30)
CONSENT_VERSION = "1"
BEARER_PREFIX = "bearer "


def now() -> datetime:
    return utcnow()


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(code: str) -> str:
    code = "".join(c for c in code.upper() if c not in " -")
    return code.translate(str.maketrans({"O": "0", "I": "1", "L": "1"}))


def format_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def code_status(code: PairingCode, at: datetime) -> str:
    if code.used_at is not None:
        return "used"
    if code.expires_at <= at:
        return "expired"
    return "pending"


async def create_pairing_code(db: AsyncSession, owner_id: int, consent: bool, ip: str) -> dict:
    if not consent:
        raise AppError(422, "consent_required")
    await db.execute(delete(PairingCode).where(PairingCode.owner_id == owner_id, PairingCode.used_at.is_(None)))
    at = now()
    code = generate_code()
    row = PairingCode(
        owner_id=owner_id,
        code_hash=hash_token(code),
        created_at=at,
        expires_at=at + CODE_TTL,
        consent_ip=ip,
    )
    db.add(row)
    await db.commit()
    return {
        "id": row.id,
        "code": format_code(code),
        "expires_at": row.expires_at,
        "expires_in": int(CODE_TTL.total_seconds()),
    }


async def get_pairing_code_status(db: AsyncSession, code_id: int, owner_id: int) -> dict:
    stmt = select(PairingCode).where(PairingCode.id == code_id, PairingCode.owner_id == owner_id)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise AppError(404, "not_found")
    return {"id": row.id, "status": code_status(row, now()), "expires_at": row.expires_at, "device_id": row.device_id}


async def _claim_code(db: AsyncSession, code: str, at: datetime) -> PairingCode:
    row = (
        await db.execute(select(PairingCode).where(PairingCode.code_hash == hash_token(normalize_code(code))))
    ).scalar_one_or_none()
    if row is None or code_status(row, at) != "pending":
        raise AppError(400, "invalid_code")
    claimed = await db.execute(
        update(PairingCode)
        .where(PairingCode.id == row.id, PairingCode.used_at.is_(None))
        .values(used_at=at)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        raise AppError(400, "invalid_code")
    return row


def _issue_tokens(db: AsyncSession, device_id: int, at: datetime) -> dict:
    access, refresh = new_token(), new_token()
    access_expires, refresh_expires = at + ACCESS_TTL, at + REFRESH_TTL
    db.add(
        DeviceToken(
            device_id=device_id,
            kind=TOKEN_ACCESS,
            token_hash=hash_token(access),
            created_at=at,
            expires_at=access_expires,
        )
    )
    db.add(
        DeviceToken(
            device_id=device_id,
            kind=TOKEN_REFRESH,
            token_hash=hash_token(refresh),
            created_at=at,
            expires_at=refresh_expires,
        )
    )
    return {
        "device_id": device_id,
        "access_token": access,
        "access_expires_at": access_expires,
        "refresh_token": refresh,
        "refresh_expires_at": refresh_expires,
    }


async def _revoke_tokens(db: AsyncSession, device_id: int, at: datetime) -> None:
    await db.execute(
        update(DeviceToken)
        .where(DeviceToken.device_id == device_id, DeviceToken.revoked_at.is_(None))
        .values(revoked_at=at)
        .execution_options(synchronize_session=False)
    )


async def enroll(
    db: AsyncSession,
    code: str,
    fingerprint: str,
    device_secret: str,
    name: str,
    accounts: list[family.NewWindowsAccount],
    ip: str,
) -> dict:
    at = now()
    row = await _claim_code(db, code, at)
    actor = audit.Actor(account_id=row.owner_id, ip=ip)
    device = await family.create_device(
        db, row.owner_id, name, hash_token(fingerprint), hash_token(device_secret), accounts, actor=actor
    )
    await db.execute(
        update(PairingCode)
        .where(PairingCode.id == row.id)
        .values(device_id=device.id)
        .execution_options(synchronize_session=False)
    )
    db.add(
        ConsentRecord(
            account_id=row.owner_id,
            device_id=device.id,
            consented_at=row.created_at,
            ip=row.consent_ip,
            consent_version=CONSENT_VERSION,
        )
    )
    tokens = _issue_tokens(db, device.id, at)
    await db.commit()
    return tokens


async def refresh(db: AsyncSession, device_id: int, refresh_token: str, device_secret: str) -> dict:
    at = now()
    token = (
        await db.execute(
            select(DeviceToken).where(
                DeviceToken.token_hash == hash_token(refresh_token), DeviceToken.kind == TOKEN_REFRESH
            )
        )
    ).scalar_one_or_none()
    device = await family.get_device(db, device_id)
    if (
        token is None
        or device is None
        or token.device_id != device.id
        or not hmac.compare_digest(device.secret_hash, hash_token(device_secret))
    ):
        raise AppError(401, "invalid_refresh")
    if device.revoked_at is not None:
        raise AppError(401, "device_revoked")
    if token.revoked_at is not None:
        await _revoke_tokens(db, device.id, at)
        await db.commit()
        raise AppError(401, "invalid_refresh")
    if token.expires_at <= at:
        raise AppError(401, "invalid_refresh")
    await _revoke_tokens(db, device.id, at)
    await db.execute(delete(DeviceToken).where(DeviceToken.device_id == device.id, DeviceToken.expires_at <= at))
    tokens = _issue_tokens(db, device.id, at)
    await db.commit()
    return tokens


async def remove_device(db: AsyncSession, device_id: int, owner_id: int, *, actor: audit.Actor) -> None:
    device = await family.revoke_device(db, device_id, owner_id, actor=actor)
    await _revoke_tokens(db, device.id, device.revoked_at)
    await db.commit()


async def current_device(request: Request, db: AsyncSession = Depends(get_db)) -> Device:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith(BEARER_PREFIX):
        raise AppError(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"})
    stmt = select(DeviceToken).where(
        DeviceToken.token_hash == hash_token(header[len(BEARER_PREFIX) :].strip()), DeviceToken.kind == TOKEN_ACCESS
    )
    token = (await db.execute(stmt)).scalar_one_or_none()
    if token is None:
        raise AppError(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"})
    device = await family.get_device(db, token.device_id)
    if device is None or device.revoked_at is not None:
        raise AppError(401, "device_revoked")
    if token.revoked_at is not None:
        raise AppError(401, "invalid_token", headers={"WWW-Authenticate": "Bearer"})
    at = now()
    if token.expires_at <= at:
        raise AppError(401, "token_expired")
    device.last_seen_at = at
    await db.commit()
    return device
