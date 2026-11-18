"""Audit log, append-only.

Three layers block updates and deletes: no API route, ORM events that raise, and SQLite triggers that ABORT.
The triggers are attached to create_all as well, so test and fresh databases match migration 0004.
old_value/new_value hold JSON of the affected fields, encrypted because they may contain children data.
"""

from datetime import datetime

from sqlalchemy import DDL, CheckConstraint, ForeignKey, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.core.db import Base, UTCDateTime

ACTIONS = ("create", "update", "delete")

NO_UPDATE_TRIGGER = (
    "CREATE TRIGGER audit_logs_no_update BEFORE UPDATE ON audit_logs "
    "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END"
)
NO_DELETE_TRIGGER = (
    "CREATE TRIGGER audit_logs_no_delete BEFORE DELETE ON audit_logs "
    "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END"
)


class AppendOnlyError(RuntimeError):
    pass


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (CheckConstraint("action IN ('create', 'update', 'delete')", name="ck_audit_logs_action"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    ip: Mapped[str] = mapped_column(String(45))
    action: Mapped[str] = mapped_column(String(16))
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[int]
    old_value: Mapped[str | None] = mapped_column(EncryptedString("audit_logs.old_value"))
    new_value: Mapped[str | None] = mapped_column(EncryptedString("audit_logs.new_value"))


event.listen(AuditLog.__table__, "after_create", DDL(NO_UPDATE_TRIGGER))
event.listen(AuditLog.__table__, "after_create", DDL(NO_DELETE_TRIGGER))


@event.listens_for(AuditLog, "before_update")
def _no_update(*_args) -> None:
    raise AppendOnlyError("audit_logs is append-only")


@event.listens_for(AuditLog, "before_delete")
def _no_delete(*_args) -> None:
    raise AppendOnlyError("audit_logs is append-only")
