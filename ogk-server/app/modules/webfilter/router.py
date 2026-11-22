from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.audit.service import Actor, current_actor
from app.modules.auth.models import Account
from app.modules.auth.service import require_admin, require_parent
from app.modules.family.service import get_child_for_owner
from app.modules.policy.service import WEB_CATEGORIES
from app.modules.webfilter import service
from app.modules.webfilter.schemas import CatalogChange

admin_router = APIRouter(prefix="/api/admin/webfilter", tags=["webfilter"], dependencies=[Depends(require_admin)])
parent_router = APIRouter(prefix="/api/children", tags=["webfilter"], dependencies=[Depends(require_parent)])


@parent_router.get("/{child_id}/webfilter/categories")
async def categories(child_id: int, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)):
    await get_child_for_owner(db, child_id, account.id)
    return {"categories": list(WEB_CATEGORIES)}


@admin_router.get("/catalog")
async def catalog(db: AsyncSession = Depends(get_db)):
    return await service.list_catalog(db)


@admin_router.put("/catalog/{domain}")
async def update_catalog(
    domain: str,
    body: CatalogChange,
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_catalog(db, domain, body.category, actor)
