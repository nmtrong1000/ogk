from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime

MIN_QUOTA_MINUTES = 0
MAX_QUOTA_MINUTES = 1440
DEFAULT_QUOTA_MINUTES = 120


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_policies_version"),
        CheckConstraint("daily_quota_minutes BETWEEN 0 AND 1440", name="ck_policies_daily_quota_minutes"),
    )

    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int]
    daily_quota_minutes: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
