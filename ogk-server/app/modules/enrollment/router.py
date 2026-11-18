"""device_router serves the agent: it authenticates with device tokens, not cookies, so main.py exempts
its prefixes from CSRF. Its paths must not share a prefix with any cookie-authenticated route.
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import client_ip, rate_limit
from app.modules.audit.service import Actor, current_actor
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.enrollment import service
from app.modules.enrollment.schemas import (
    DeviceMeOut,
    EnrollIn,
    PairingCodeCreate,
    PairingCodeOut,
    PairingCodeStatusOut,
    RefreshIn,
    TokensOut,
)
from app.modules.family.models import Device
from app.modules.family.service import NewWindowsAccount

DEVICE_PREFIXES = ("/api/enroll", "/api/device/")

router = APIRouter(tags=["enrollment"], dependencies=[Depends(require_parent)])
device_router = APIRouter(tags=["device"])


@router.post(
    "/api/pairing-codes", status_code=201, response_model=PairingCodeOut, dependencies=[rate_limit("pairing_code", 10)]
)
async def create_pairing_code(
    body: PairingCodeCreate,
    request: Request,
    account: Account = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_pairing_code(db, account.id, body.consent, client_ip(request))


@router.get("/api/pairing-codes/{code_id}", response_model=PairingCodeStatusOut)
async def get_pairing_code(
    code_id: int, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)
):
    return await service.get_pairing_code_status(db, code_id, account.id)


@router.delete("/api/devices/{device_id}", status_code=204)
async def remove_device(
    device_id: int,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await service.remove_device(db, device_id, account.id, actor=actor)
    return Response(status_code=204)


@device_router.post("/api/enroll", status_code=201, response_model=TokensOut, dependencies=[rate_limit("enroll", 10)])
async def enroll(body: EnrollIn, request: Request, db: AsyncSession = Depends(get_db)):
    accounts = [NewWindowsAccount(sid=a.sid, username=a.username) for a in body.accounts]
    return await service.enroll(
        db, body.code, body.fingerprint, body.device_secret, body.name, accounts, client_ip(request)
    )


@device_router.post("/api/device/token/refresh", response_model=TokensOut, dependencies=[rate_limit("refresh", 30)])
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    return await service.refresh(db, body.device_id, body.refresh_token, body.device_secret)


@device_router.get("/api/device/me", response_model=DeviceMeOut)
async def device_me(device: Device = Depends(service.current_device)):
    return {"id": device.id, "name": device.name}
