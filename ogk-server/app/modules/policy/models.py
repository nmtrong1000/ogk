"""weekly_schedule stores the 7 x 48 grid as one 336-character string, Monday first; the service checks it holds
only 0 and 1 because SQLite has no portable regex CHECK.
app_rules stores the normalized rule list as canonical JSON text so it is copied, compared and snapshotted like
the other rule columns; the CHECK only proves it is a JSON array, the service validates each rule.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
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
EMPTY_APP_RULES = "[]"
EMPTY_DOMAIN_RULES = "[]"
EMPTY_BLOCKED_CATEGORIES = '["adult","social"]'


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_policies_version"),
        CheckConstraint("weekday_quota_minutes BETWEEN 0 AND 1440", name="ck_policies_weekday_quota_minutes"),
        CheckConstraint("weekend_quota_minutes BETWEEN 0 AND 1440", name="ck_policies_weekend_quota_minutes"),
        CheckConstraint("length(weekly_schedule) = 336", name="ck_policies_weekly_schedule"),
        CheckConstraint("json_valid(app_rules) AND json_type(app_rules) = 'array'", name="ck_policies_app_rules"),
        CheckConstraint(
            "json_valid(web_allowlist) AND json_type(web_allowlist) = 'array'", name="ck_policies_web_allowlist"
        ),
        CheckConstraint(
            "json_valid(web_blocklist) AND json_type(web_blocklist) = 'array'", name="ck_policies_web_blocklist"
        ),
        CheckConstraint(
            "json_valid(blocked_categories) AND json_type(blocked_categories) = 'array'",
            name="ck_policies_blocked_categories",
        ),
    )

    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int]
    weekday_quota_minutes: Mapped[int]
    weekend_quota_minutes: Mapped[int]
    weekly_schedule: Mapped[str] = mapped_column(String(SCHEDULE_LENGTH))
    app_rules: Mapped[str] = mapped_column(Text, default=EMPTY_APP_RULES)
    web_allowlist: Mapped[str] = mapped_column(Text, default=EMPTY_DOMAIN_RULES)
    web_blocklist: Mapped[str] = mapped_column(Text, default=EMPTY_DOMAIN_RULES)
    blocked_categories: Mapped[str] = mapped_column(Text, default=EMPTY_BLOCKED_CATEGORIES)
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
        CheckConstraint(
            "json_valid(app_rules) AND json_type(app_rules) = 'array'", name="ck_policy_versions_app_rules"
        ),
        CheckConstraint(
            "json_valid(web_allowlist) AND json_type(web_allowlist) = 'array'", name="ck_policy_versions_web_allowlist"
        ),
        CheckConstraint(
            "json_valid(web_blocklist) AND json_type(web_blocklist) = 'array'", name="ck_policy_versions_web_blocklist"
        ),
        CheckConstraint(
            "json_valid(blocked_categories) AND json_type(blocked_categories) = 'array'",
            name="ck_policy_versions_blocked_categories",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    version: Mapped[int]
    weekday_quota_minutes: Mapped[int]
    weekend_quota_minutes: Mapped[int]
    weekly_schedule: Mapped[str] = mapped_column(String(SCHEDULE_LENGTH))
    app_rules: Mapped[str] = mapped_column(Text, default=EMPTY_APP_RULES)
    web_allowlist: Mapped[str] = mapped_column(Text, default=EMPTY_DOMAIN_RULES)
    web_blocklist: Mapped[str] = mapped_column(Text, default=EMPTY_DOMAIN_RULES)
    blocked_categories: Mapped[str] = mapped_column(Text, default=EMPTY_BLOCKED_CATEGORIES)
    set_by: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
