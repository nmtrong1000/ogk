"""device_router lives under /api/device/, which main.py exempts from CSRF because the agent sends no cookies.
The events body is read raw so malformed batches return invalid_batch or invalid_event instead of FastAPI's 422.
"""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.enrollment.service import current_device
from app.modules.family.models import Device
from app.modules.sync import service
from app.modules.sync.schemas import AlertOut, EventsOut, HeartbeatIn, HeartbeatOut

router = APIRouter(prefix="/api/alerts", tags=["sync"], dependencies=[Depends(require_parent)])
device_router = APIRouter(tags=["device"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    device_id: int | None = None, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)
):
    return await service.list_alerts(db, account.id, device_id)


@device_router.post("/api/device/heartbeat", response_model=HeartbeatOut)
async def heartbeat(body: HeartbeatIn, device: Device = Depends(current_device), db: AsyncSession = Depends(get_db)):
    return await service.heartbeat(db, device, body)


@device_router.post("/api/device/events", response_model=EventsOut)
async def post_events(
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    device: Device = Depends(current_device),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await request.json()
    except ValueError as exc:
        raise AppError(422, "invalid_batch") from exc
    return await service.receive_events(db, device, idempotency_key, payload)
