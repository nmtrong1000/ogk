from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.audit.service import Actor, current_actor
from app.modules.auth.models import Account
from app.modules.auth.service import require_parent
from app.modules.family import service
from app.modules.family.schemas import ChildCreate, ChildOut, ChildUpdate

router = APIRouter(prefix="/api/children", tags=["family"], dependencies=[Depends(require_parent)])


@router.get("", response_model=list[ChildOut])
async def list_children(account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)):
    return await service.list_children(db, account.id)


@router.post("", status_code=201, response_model=ChildOut)
async def create_child(
    body: ChildCreate,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_child(db, account.id, body.name, body.birth_year, actor=actor)


@router.get("/{child_id}", response_model=ChildOut)
async def get_child(child_id: int, account: Account = Depends(require_parent), db: AsyncSession = Depends(get_db)):
    return await service.get_child_for_owner(db, child_id, account.id)


@router.patch("/{child_id}", response_model=ChildOut)
async def update_child(
    child_id: int,
    body: ChildUpdate,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_child(db, child_id, account.id, body.name, body.birth_year, actor=actor)


@router.delete("/{child_id}", status_code=204)
async def delete_child(
    child_id: int,
    account: Account = Depends(require_parent),
    actor: Actor = Depends(current_actor),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await service.delete_child(db, child_id, account.id, actor=actor)
    return Response(status_code=204)
