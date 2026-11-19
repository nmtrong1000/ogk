"""device_router lives under /api/device/, which main.py exempts from CSRF because the agent sends no cookies."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.audit.service import Actor, current_actor
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.enrollment.service import current_device
from app.modules.family.models import Device
from app.modules.policy import service
from app.modules.policy.schemas import DevicePoliciesOut, PolicyOut, PolicyUpdate, PolicyVersionOut

router = APIRouter(prefix="/api/children", tags=["policy"], dependencies=[Depends(require_parent)])
device_router = APIRouter(tags=["device"])


@router.get("/{child_id}/policy", response_model=PolicyOut)
async def get_policy(child_id: int, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)):
    return await service.get_policy(db, child_id, account.id)


@router.patch("/{child_id}/policy", response_model=PolicyOut)
async def update_policy(
    child_id: int,
    body: PolicyUpdate,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_policy(db, child_id, account.id, body.model_dump(), actor=actor)


@router.get("/{child_id}/policy/versions", response_model=list[PolicyVersionOut])
async def list_versions(child_id: int, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)):
    return await service.list_versions(db, child_id, account.id)


@device_router.get("/api/device/policy", response_model=DevicePoliciesOut)
async def device_policy(device: Device = Depends(current_device), db: AsyncSession = Depends(get_db)):
    return await service.device_policies(db, device)
