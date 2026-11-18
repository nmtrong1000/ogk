from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.audit import service
from app.modules.audit.schemas import AuditPageOut
from app.modules.auth.models import ROLE_ADMIN, ROLE_PARENT, Account
from app.modules.auth.service import require_role

router = APIRouter(prefix="/api/audit", tags=["audit"])

require_viewer = require_role(ROLE_PARENT, ROLE_ADMIN)


@router.get("", response_model=AuditPageOut)
async def list_audit(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=service.MAX_PAGE_SIZE),
    account: Account = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_logs(db, account, page, size)
