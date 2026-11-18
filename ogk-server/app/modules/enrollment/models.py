"""Only SHA-256 hashes of pairing codes and device tokens are stored; the plain values exist only in responses.
pairing_codes uses AUTOINCREMENT: unused codes are deleted when a new one is made, and a reused id would let
a dashboard still polling the old code read the new code's status.
A device token with revoked_at set is kept until it expires so reuse of a rotated refresh token can be detected.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime

TOKEN_ACCESS = "access"
TOKEN_REFRESH = "refresh"


class PairingCode(Base):
    __tablename__ = "pairing_codes"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))
    consent_ip: Mapped[str] = mapped_column(String(45))


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (CheckConstraint("kind IN ('access', 'refresh')", name="ck_device_tokens_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    consented_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ip: Mapped[str] = mapped_column(String(45))
    consent_version: Mapped[str] = mapped_column(String(16))
