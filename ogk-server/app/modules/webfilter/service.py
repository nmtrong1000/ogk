import re
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.audit import service as audit
from app.modules.policy import service as policy_service
from app.modules.policy.models import Policy
from app.modules.webfilter.models import CATEGORIES, WebCategory

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def normalize_domain(value: str) -> str:
    domain = value.strip().rstrip(".").lower()
    if not DOMAIN_RE.fullmatch(domain):
        raise AppError(422, "invalid_domain")
    return domain


async def list_catalog(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(WebCategory).order_by(WebCategory.category, WebCategory.domain))).scalars()
    return [{"domain": row.domain, "category": row.category, "updated_at": row.updated_at} for row in rows]


async def update_catalog(db: AsyncSession, domain: str, category: str | None, actor: audit.Actor) -> dict | None:
    domain = normalize_domain(domain)
    if category is not None and category not in CATEGORIES:
        raise AppError(422, "invalid_category")
    row = await db.get(WebCategory, domain)
    old = None if row is None else {"domain": row.domain, "category": row.category}
    if category is None:
        if row is None:
            raise AppError(404, "not_found")
        count = (await db.execute(select(func.count()).select_from(WebCategory))).scalar_one()
        if count <= 200:
            raise AppError(422, "catalog_minimum_size")
        await db.delete(row)
        new = None
    elif row is None:
        count = (await db.execute(select(func.count()).select_from(WebCategory))).scalar_one()
        if count >= 1000:
            raise AppError(422, "catalog_maximum_size")
        row = WebCategory(domain=domain, category=category, updated_at=datetime.now(UTC))
        db.add(row)
        new = {"domain": domain, "category": category}
    elif row.category != category:
        row.category = category
        row.updated_at = datetime.now(UTC)
        new = {"domain": domain, "category": category}
    else:
        return {"domain": row.domain, "category": row.category, "updated_at": row.updated_at}
    policies = list((await db.execute(select(Policy))).scalars())
    for policy in policies:
        await policy_service._bump(db, policy.child_id, {}, actor)
    audit.record(
        db,
        actor,
        "delete" if category is None else ("create" if old is None else "update"),
        "web_category",
        0,
        old,
        new,
    )
    await db.commit()
    return (
        None
        if row is None or category is None
        else {"domain": row.domain, "category": row.category, "updated_at": row.updated_at}
    )
