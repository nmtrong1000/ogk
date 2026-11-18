"""children uses AUTOINCREMENT so a deleted child's id is never reused and audit entries never point at another child."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedInt, EncryptedString
from app.core.db import Base, UTCDateTime


class Child(Base):
    __tablename__ = "children"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(EncryptedString("children.name"))
    birth_year: Mapped[int] = mapped_column(EncryptedInt("children.birth_year"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class WindowsAccount(Base):
    __tablename__ = "windows_accounts"
    __table_args__ = (UniqueConstraint("device_id", "sid", name="uq_windows_accounts_device_sid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[int | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"), index=True)
    sid: Mapped[str] = mapped_column(String(184))
    username: Mapped[str] = mapped_column(EncryptedString("windows_accounts.username"))
