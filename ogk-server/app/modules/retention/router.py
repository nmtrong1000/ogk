from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.audit.service import Actor, current_actor
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.retention import service
from app.modules.retention.schemas import WipeOut

router = APIRouter(prefix="/api/children", tags=["retention"], dependencies=[Depends(require_parent)])


@router.delete("/{child_id}/data", response_model=WipeOut)
async def wipe_child_data(
    child_id: int,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
):
    return await service.wipe_child(db, child_id, account.id, actor)
