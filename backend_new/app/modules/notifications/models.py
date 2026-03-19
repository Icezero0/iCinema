from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.notifications.constants import (
    NotificationRelatedType,
    NotificationType,
)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    recipient_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    related_type: Mapped[NotificationRelatedType | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    related_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    recipient = relationship("User", foreign_keys=[recipient_user_id])
    actor = relationship("User", foreign_keys=[actor_user_id])