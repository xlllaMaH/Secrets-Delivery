import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("max_views >= 1", name="ck_notes_max_views_positive"),
        CheckConstraint(
            "views_count >= 0 AND views_count <= max_views",
            name="ck_notes_views_count_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(32), unique=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[bytes | None] = mapped_column(LargeBinary)
    max_views: Mapped[int] = mapped_column(default=1, server_default="1")
    views_count: Mapped[int] = mapped_column(default=0, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
