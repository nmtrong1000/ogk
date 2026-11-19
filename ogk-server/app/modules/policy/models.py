"""weekly_schedule stores the 7 x 48 grid as one 336-character string, Monday first; the service checks it holds
only 0 and 1 because SQLite has no portable regex CHECK.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime

MIN_QUOTA_MINUTES = 0
MAX_QUOTA_MINUTES = 1440
DEFAULT_QUOTA_MINUTES = 120
DAYS_PER_WEEK = 7
SLOTS_PER_DAY = 48
SCHEDULE_LENGTH = DAYS_PER_WEEK * SLOTS_PER_DAY
DEFAULT_DAY = "0" * 14 + "1" * 28 + "0" * 6
DEFAULT_SCHEDULE = DEFAULT_DAY * DAYS_PER_WEEK


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_policies_version"),
        CheckConstraint("weekday_quota_minutes BETWEEN 0 AND 1440", name="ck_policies_weekday_quota_minutes"),
        CheckConstraint("weekend_quota_minutes BETWEEN 0 AND 1440", name="ck_policies_weekend_quota_minutes"),
        CheckConstraint("length(weekly_schedule) = 336", name="ck_policies_weekly_schedule"),
    )

    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int]
    weekday_quota_minutes: Mapped[int]
    weekend_quota_minutes: Mapped[int]
    weekly_schedule: Mapped[str] = mapped_column(String(SCHEDULE_LENGTH))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("child_id", "version", name="uq_policy_versions_child_version"),
        CheckConstraint("version >= 1", name="ck_policy_versions_version"),
        CheckConstraint("weekday_quota_minutes BETWEEN 0 AND 1440", name="ck_policy_versions_weekday_quota_minutes"),
        CheckConstraint("weekend_quota_minutes BETWEEN 0 AND 1440", name="ck_policy_versions_weekend_quota_minutes"),
        CheckConstraint("length(weekly_schedule) = 336", name="ck_policy_versions_weekly_schedule"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    version: Mapped[int]
    weekday_quota_minutes: Mapped[int]
    weekend_quota_minutes: Mapped[int]
    weekly_schedule: Mapped[str] = mapped_column(String(SCHEDULE_LENGTH))
    set_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
