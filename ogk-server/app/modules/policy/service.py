"""A policy row and its version-1 history row are created lazily the first time a child's policy is read.
The version is bumped inside the UPDATE statement so two concurrent edits never share a version number.
issued_at is the row's updated_at, so the same version always signs to the same bytes as long as the
child's SIDs on that device are unchanged; assigning an account bumps the version for exactly that reason.
record_version() and bump_for_accounts() do not commit; the caller commits with its audit entry.
App rules are normalized (lowercase, sorted) before they are stored, so an edit that only reorders or recases
the list is not a change and the stored text compares equal to the new one.
"""

import json
import re
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import signing
from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.audit import service as audit
from app.modules.auth import service as auth
from app.modules.family import service as family
from app.modules.family.models import Device
from app.modules.policy.models import (
    DAYS_PER_WEEK,
    DEFAULT_QUOTA_MINUTES,
    DEFAULT_SCHEDULE,
    EMPTY_APP_RULES,
    EMPTY_BLOCKED_CATEGORIES,
    EMPTY_DOMAIN_RULES,
    MAX_QUOTA_MINUTES,
    MIN_QUOTA_MINUTES,
    SLOTS_PER_DAY,
    Policy,
    PolicyVersion,
)
from app.modules.webfilter.models import WebCategory

FORMAT = 1
AUDIT_TARGET = "policy"
MAX_VERSIONS = 50
RULE_FIELDS = (
    "weekday_quota_minutes",
    "weekend_quota_minutes",
    "weekly_schedule",
    "app_rules",
    "web_allowlist",
    "web_blocklist",
    "blocked_categories",
)
MAX_APP_RULES = 200
MAX_APP_NAME = 255
APP_ACTIONS = ("allow", "block")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
WEB_CATEGORIES = ("education", "entertainment", "social", "games", "adult", "unclassified")


def now() -> datetime:
    return utcnow()


def iso(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_quota(minutes: int) -> int:
    if not MIN_QUOTA_MINUTES <= minutes <= MAX_QUOTA_MINUTES:
        raise AppError(422, "invalid_quota")
    return minutes


def validate_schedule(days: list[str]) -> str:
    if len(days) != DAYS_PER_WEEK or any(len(day) != SLOTS_PER_DAY or set(day) - {"0", "1"} for day in days):
        raise AppError(422, "invalid_schedule")
    return "".join(days)


def _app_rule(rule: dict) -> dict:
    name, sha256, action = rule.get("name"), rule.get("sha256"), rule.get("action")
    if not isinstance(name, str) or not isinstance(action, str):
        raise AppError(422, "invalid_app_rules")
    name = name.strip().lower()
    if not 1 <= len(name) <= MAX_APP_NAME or "/" in name or "\\" in name or not name.isprintable():
        raise AppError(422, "invalid_app_rules")
    if sha256 is not None:
        if not isinstance(sha256, str) or not SHA256_RE.match(sha256.strip().lower()):
            raise AppError(422, "invalid_app_rules")
        sha256 = sha256.strip().lower()
    if action not in APP_ACTIONS:
        raise AppError(422, "invalid_app_rules")
    return {"action": action, "name": name, "sha256": sha256}


def validate_app_rules(items: list[dict]) -> str:
    if len(items) > MAX_APP_RULES:
        raise AppError(422, "invalid_app_rules")
    normalized = [_app_rule(item) for item in items]
    pairs = {(r["name"], r["sha256"]) for r in normalized}
    if len(pairs) != len(normalized):
        raise AppError(422, "invalid_app_rules")
    normalized.sort(key=lambda r: (r["name"], r["sha256"] or "", r["action"]))
    return dump_app_rules(normalized)


def dump_app_rules(items: list[dict]) -> str:
    return json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_domain_rules(items: list[str]) -> str:
    if len(items) > 1000 or any(not isinstance(item, str) for item in items):
        raise AppError(422, "invalid_domain_rules")
    normalized = []
    for item in items:
        domain = item.strip().rstrip(".").lower()
        if not DOMAIN_RE.fullmatch(domain):
            raise AppError(422, "invalid_domain_rules")
        normalized.append(domain)
    return json.dumps(sorted(set(normalized)), separators=(",", ":"))


def validate_blocked_categories(items: list[str]) -> str:
    if len(items) > len(WEB_CATEGORIES) or any(item not in WEB_CATEGORIES for item in items):
        raise AppError(422, "invalid_blocked_categories")
    return json.dumps(sorted(set(items)), separators=(",", ":"))


def schedule_days(schedule: str) -> list[str]:
    return [schedule[i : i + SLOTS_PER_DAY] for i in range(0, len(schedule), SLOTS_PER_DAY)]


def rules(row: Policy | PolicyVersion) -> dict:
    return {
        "weekday_quota_minutes": row.weekday_quota_minutes,
        "weekend_quota_minutes": row.weekend_quota_minutes,
        "weekly_schedule": schedule_days(row.weekly_schedule),
        "app_rules": json.loads(row.app_rules),
        "web_allowlist": json.loads(row.web_allowlist),
        "web_blocklist": json.loads(row.web_blocklist),
        "blocked_categories": json.loads(row.blocked_categories),
    }


def policy_out(policy: Policy, set_by: str | None) -> dict:
    return {
        "child_id": policy.child_id,
        "policy_version": policy.version,
        **rules(policy),
        "set_by": set_by,
        "updated_at": policy.updated_at,
    }


def document(
    policy: Policy, accounts: list[str], set_by: str | None, category_domains: dict[str, list[str]] | None = None
) -> dict:
    return {
        "accounts": sorted(accounts),
        "child_id": policy.child_id,
        "format": FORMAT,
        "issued_at": iso(policy.updated_at),
        "policy_version": policy.version,
        "rules": {**rules(policy), "category_domains": category_domains or {}},
        "set_by": set_by or "",
    }


def signed(policy: Policy, accounts: list[str], set_by: str | None, category_domains: dict[str, list[str]]) -> dict:
    doc = document(policy, accounts, set_by, category_domains)
    return {"policy": doc, "signature": signing.sign(doc), "key_id": signing.signing_key_id()}


def record_version(db: AsyncSession, policy: Policy) -> None:
    db.add(
        PolicyVersion(
            child_id=policy.child_id,
            version=policy.version,
            weekday_quota_minutes=policy.weekday_quota_minutes,
            weekend_quota_minutes=policy.weekend_quota_minutes,
            weekly_schedule=policy.weekly_schedule,
            app_rules=policy.app_rules,
            web_allowlist=policy.web_allowlist,
            web_blocklist=policy.web_blocklist,
            blocked_categories=policy.blocked_categories,
            set_by=policy.updated_by,
            created_at=policy.updated_at,
        )
    )


async def ensure_policies(db: AsyncSession, child_ids: list[int]) -> list[Policy]:
    if not child_ids:
        return []
    at = now()
    owners = await family.owner_ids(db, child_ids)
    rows = [
        {
            "child_id": cid,
            "version": 1,
            "weekday_quota_minutes": DEFAULT_QUOTA_MINUTES,
            "weekend_quota_minutes": DEFAULT_QUOTA_MINUTES,
            "weekly_schedule": DEFAULT_SCHEDULE,
            "app_rules": EMPTY_APP_RULES,
            "web_allowlist": EMPTY_DOMAIN_RULES,
            "web_blocklist": EMPTY_DOMAIN_RULES,
            "blocked_categories": EMPTY_BLOCKED_CATEGORIES,
            "updated_by": owners.get(cid),
            "updated_at": at,
        }
        for cid in child_ids
    ]
    stmt = insert(Policy).values(rows).on_conflict_do_nothing(index_elements=["child_id"]).returning(Policy.child_id)
    created = set((await db.execute(stmt)).scalars())
    policies = list(
        (await db.execute(select(Policy).where(Policy.child_id.in_(child_ids)).order_by(Policy.child_id))).scalars()
    )
    for policy in policies:
        if policy.child_id in created:
            record_version(db, policy)
    await db.commit()
    return policies


async def _email(db: AsyncSession, account_id: int | None) -> str | None:
    if account_id is None:
        return None
    return (await auth.emails_by_ids(db, {account_id})).get(account_id)


async def get_policy(db: AsyncSession, child_id: int, owner_id: int) -> dict:
    child = await family.get_child_for_owner(db, child_id, owner_id)
    (policy,) = await ensure_policies(db, [child.id])
    return policy_out(policy, await _email(db, policy.updated_by))


async def _bump(db: AsyncSession, child_id: int, values: dict, actor: audit.Actor) -> Policy:
    stmt = (
        update(Policy)
        .where(Policy.child_id == child_id)
        .values(version=Policy.version + 1, updated_by=actor.account_id, updated_at=now(), **values)
        .returning(Policy)
        .execution_options(synchronize_session=False, populate_existing=True)
    )
    policy = (await db.execute(stmt)).scalar_one()
    record_version(db, policy)
    return policy


def _audit_values(values: dict) -> dict:
    json_fields = {"app_rules", "web_allowlist", "web_blocklist", "blocked_categories"}
    return {f: json.loads(v) if f in json_fields else v for f, v in values.items()}


async def update_policy(db: AsyncSession, child_id: int, owner_id: int, changes: dict, *, actor: audit.Actor) -> dict:
    child = await family.get_child_for_owner(db, child_id, owner_id)
    values: dict = {}
    for field in ("weekday_quota_minutes", "weekend_quota_minutes"):
        if changes.get(field) is not None:
            values[field] = validate_quota(changes[field])
    if changes.get("weekly_schedule") is not None:
        values["weekly_schedule"] = validate_schedule(changes["weekly_schedule"])
    if changes.get("app_rules") is not None:
        values["app_rules"] = validate_app_rules(changes["app_rules"])
    if changes.get("web_allowlist") is not None:
        values["web_allowlist"] = validate_domain_rules(changes["web_allowlist"])
    if changes.get("web_blocklist") is not None:
        values["web_blocklist"] = validate_domain_rules(changes["web_blocklist"])
    if changes.get("blocked_categories") is not None:
        values["blocked_categories"] = validate_blocked_categories(changes["blocked_categories"])
    (policy,) = await ensure_policies(db, [child.id])
    values = {field: value for field, value in values.items() if getattr(policy, field) != value}
    if not values:
        return policy_out(policy, await _email(db, policy.updated_by))
    old = {**_audit_values({field: getattr(policy, field) for field in values}), "policy_version": policy.version}
    policy = await _bump(db, child.id, values, actor)
    new = {**_audit_values(values), "policy_version": policy.version}
    audit.record(db, actor, "update", AUDIT_TARGET, child.id, old, new)
    await db.commit()
    return policy_out(policy, await _email(db, policy.updated_by))


async def bump_for_accounts(db: AsyncSession, child_ids: list[int], *, actor: audit.Actor) -> None:
    existing = (await db.execute(select(Policy.child_id).where(Policy.child_id.in_(child_ids)))).scalars()
    for child_id in sorted(set(existing)):
        await _bump(db, child_id, {}, actor)


async def list_versions(db: AsyncSession, child_id: int, owner_id: int) -> list[dict]:
    child = await family.get_child_for_owner(db, child_id, owner_id)
    await ensure_policies(db, [child.id])
    stmt = (
        select(PolicyVersion)
        .where(PolicyVersion.child_id == child.id)
        .order_by(PolicyVersion.version.desc())
        .limit(MAX_VERSIONS)
    )
    versions = list((await db.execute(stmt)).scalars())
    emails = await auth.emails_by_ids(db, {v.set_by for v in versions if v.set_by is not None})
    return [
        {"policy_version": v.version, **rules(v), "set_by": emails.get(v.set_by), "created_at": v.created_at}
        for v in versions
    ]


async def device_policies(db: AsyncSession, device: Device) -> dict:
    sids = await family.sids_by_child_on_device(db, device.id)
    policies = await ensure_policies(db, sorted(sids))
    emails = await auth.emails_by_ids(db, {p.updated_by for p in policies if p.updated_by is not None})
    rows = (await db.execute(select(WebCategory).order_by(WebCategory.domain))).scalars()
    category_domains: dict[str, list[str]] = {}
    for row in rows:
        category_domains.setdefault(row.category, []).append(row.domain)
    return {"policies": [signed(p, sids[p.child_id], emails.get(p.updated_by), category_domains) for p in policies]}
