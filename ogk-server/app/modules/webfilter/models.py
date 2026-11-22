from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime
from app.modules.webfilter.catalog_data import catalog_rows

CATEGORIES = ("education", "entertainment", "social", "games", "adult", "unclassified")


class WebCategory(Base):
    __tablename__ = "web_categories"
    __table_args__ = (
        CheckConstraint(
            "category IN ('education', 'entertainment', 'social', 'games', 'adult', 'unclassified')",
            name="ck_web_categories_category",
        ),
    )

    domain: Mapped[str] = mapped_column(String(253), primary_key=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())


def _seed_catalog(_table, connection, **_kwargs) -> None:
    at = datetime.now(UTC)
    connection.execute(
        WebCategory.__table__.insert(),
        [{"domain": domain, "category": category, "updated_at": at} for domain, category in catalog_rows()],
    )


event.listen(WebCategory.__table__, "after_create", _seed_catalog)
