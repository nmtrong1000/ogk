"""Development seed data, created through the module services so audit entries, policy versions and the
encryption of names happen exactly as they would through the API.
Every seed account shares the password from OGK_SEED_PASSWORD; without it the command refuses to run, which
keeps it from being used on a real deployment by accident. Seeding runs once: if the seed admin already
exists nothing is created, so running it again is safe.
The sample device can never connect: its secret is random and thrown away. A real agent pairs with the
code from --pairing-code instead.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import Actor
from app.modules.auth import service as auth
from app.modules.auth.models import ROLE_ADMIN
from app.modules.enrollment import service as enrollment
from app.modules.family import service as family
from app.modules.policy import service as policy
from app.modules.sync import service as sync
from app.modules.sync.schemas import AlertIn, EnforcementIn, HeartbeatIn, StatusIn

SEED_IP = "127.0.0.1"
ADMIN_EMAIL = "admin@ogk.local"
PARENT1_EMAIL = "phuhuynh1@ogk.local"
PARENT2_EMAIL = "phuhuynh2@ogk.local"
SEED_DOMAIN = "S-1-5-21-900000001-900000002-900000003"
EVENT_DAYS = 7


def window(start: str, end: str) -> str:
    def slot(hhmm: str) -> int:
        hours, minutes = hhmm.split(":")
        return int(hours) * 2 + int(minutes) // 30

    first, last = slot(start), slot(end)
    return "0" * first + "1" * (last - first) + "0" * (48 - last)


@dataclass(frozen=True)
class ChildSeed:
    name: str
    birth_year: int
    weekday_minutes: int | None = None
    weekend_minutes: int | None = None
    weekday_hours: tuple[str, str] | None = None
    weekend_hours: tuple[str, str] | None = None
    username: str | None = None


@dataclass(frozen=True)
class ParentSeed:
    email: str
    children: list[ChildSeed]
    device_name: str | None = None
    parent_username: str | None = None


PARENTS = [
    ParentSeed(
        PARENT1_EMAIL,
        [
            ChildSeed("An", 2015, 120, 180, ("16:00", "21:00"), ("08:00", "21:00"), "an"),
            ChildSeed("Bình", 2018, 60, 120, ("17:00", "20:00"), ("08:00", "20:00"), "binh"),
        ],
        device_name="PC phòng khách (dữ liệu mẫu)",
        parent_username="bo",
    ),
    ParentSeed(PARENT2_EMAIL, [ChildSeed("Chi", 2012), ChildSeed("Dũng", 2019, 45, 90)]),
]


@dataclass
class SeedReport:
    created: bool
    accounts: list[str] = field(default_factory=list)
    children: dict[str, list[str]] = field(default_factory=dict)
    devices: list[str] = field(default_factory=list)
    events: int = 0
    pairing_code: str | None = None


def schedule_for(child: ChildSeed) -> list[str] | None:
    if child.weekday_hours is None or child.weekend_hours is None:
        return None
    return [window(*child.weekday_hours)] * 5 + [window(*child.weekend_hours)] * 2


def _ts(at: datetime) -> str:
    return at.strftime("%Y-%m-%dT%H:%M:%SZ")


def sample_events(device_id: int, children: dict[str, int], versions: dict[int, int], now: datetime) -> list[dict]:
    events = []

    def add(at: datetime, child_id: int, kind: str, subject: str, duration: int) -> None:
        events.append(
            {
                "ts": _ts(at),
                "device_id": device_id,
                "child_id": child_id,
                "type": kind,
                "subject": subject,
                "duration_sec": duration,
                "policy_id": versions[child_id],
            }
        )

    for day in range(EVENT_DAYS, 0, -1):
        base = (now - timedelta(days=day)).replace(hour=10, minute=0, second=0, microsecond=0)
        for offset, child_id in enumerate(sorted(children.values())):
            start = base + timedelta(minutes=30 * offset)
            add(start, child_id, "app_start", "chrome.exe", 0)
            add(start + timedelta(minutes=2), child_id, "domain_query", "wikipedia.org", 0)
            add(start + timedelta(minutes=5), child_id, "domain_query", "youtube.com", 0)
            add(start + timedelta(minutes=50), child_id, "app_stop", "chrome.exe", 3000)
            if (day + offset) % 2 == 0:
                for minutes_left, used in (("10", 3000), ("5", 3300), ("1", 3540)):
                    add(start + timedelta(seconds=used), child_id, "quota_warning", minutes_left, used)
                add(start + timedelta(seconds=3660), child_id, "locked", "quota", 3660)
        if day == 2:
            add(base.replace(hour=14), sorted(children.values())[0], "locked", "schedule", 600)
    return events


async def _heartbeat(db: AsyncSession, device, alerts: list[AlertIn]) -> None:
    status = StatusIn(uptime=60.0, enforcement=EnforcementIn(enabled=True), policy_mode="cached")
    await sync.heartbeat(db, device, HeartbeatIn(status=status, alerts=alerts))


async def _seed_device(db: AsyncSession, parent_id: int, spec: ParentSeed, children: dict[str, int], now: datetime):
    actor = Actor(parent_id, SEED_IP)
    accounts = [
        family.NewWindowsAccount(f"{SEED_DOMAIN}-{1001 + i}", child.username)
        for i, child in enumerate(spec.children)
        if child.username
    ]
    if spec.parent_username:
        accounts.append(family.NewWindowsAccount(f"{SEED_DOMAIN}-1500", spec.parent_username))
    device = await family.create_device(
        db,
        parent_id,
        spec.device_name,
        hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
        hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
        accounts,
        actor=actor,
    )
    await db.commit()
    for child in spec.children:
        if child.username:
            sid = next(a.sid for a in accounts if a.username == child.username)
            account = await family.windows_account_by_sid(db, device.id, sid)
            await family.assign_account(db, device.id, account.id, children[child.name], parent_id, actor=actor)
    versions = {p.child_id: p.version for p in await policy.ensure_policies(db, sorted(children.values()))}
    events = sample_events(device.id, children, versions, now)
    for start in range(0, len(events), 500):
        await sync.receive_events(db, device, f"seed-{start}", {"events": events[start : start + 500]})
    tampered = AlertIn(type="clock_tampered", detail="backward", ts=now - timedelta(hours=3))
    disabled = AlertIn(type="enforcement_disabled", detail="tray_unavailable", ts=now - timedelta(days=1))
    await _heartbeat(db, device, [disabled])
    await _heartbeat(db, device, [tampered])
    return device, len(events)


async def seed(db: AsyncSession, password: str, now: datetime, pairing_code: bool = False) -> SeedReport:
    auth.validate_password(password)
    existing = await auth.get_by_email(db, ADMIN_EMAIL)
    report = SeedReport(created=existing is None)
    if existing is None:
        await auth.create_account(db, ADMIN_EMAIL, password, role=ROLE_ADMIN)
        report.accounts.append(ADMIN_EMAIL)
        for spec in PARENTS:
            parent = await auth.create_account(db, spec.email, password)
            report.accounts.append(spec.email)
            actor = Actor(parent.id, SEED_IP)
            children: dict[str, int] = {}
            for child in spec.children:
                created = await family.create_child(db, parent.id, child.name, child.birth_year, actor=actor)
                children[child.name] = created.id
                changes = {
                    "weekday_quota_minutes": child.weekday_minutes,
                    "weekend_quota_minutes": child.weekend_minutes,
                    "weekly_schedule": schedule_for(child),
                }
                await policy.update_policy(db, created.id, parent.id, changes, actor=actor)
            report.children[spec.email] = list(children)
            if spec.device_name:
                device, count = await _seed_device(db, parent.id, spec, children, now)
                report.devices.append(device.name)
                report.events += count
    if pairing_code:
        parent = await auth.get_by_email(db, PARENT1_EMAIL)
        code = await enrollment.create_pairing_code(db, parent.id, True, SEED_IP)
        report.pairing_code = code["code"]
    return report
