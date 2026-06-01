from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.feedback.constants import FeedbackStatus, FeedbackType


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        Index("idx_feedbacks_creator_id_created_at", "creator_id", "created_at"),
        Index("idx_feedbacks_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    creator_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    handled_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feedback_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=FeedbackType.BUG,
        server_default=FeedbackType.BUG,
    )
    page: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=FeedbackStatus.OPEN,
        server_default=FeedbackStatus.OPEN,
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    creator = relationship("User", foreign_keys=[creator_id])
    handled_by = relationship("User", foreign_keys=[handled_by_id])
    screenshots = relationship(
        "FeedbackScreenshot",
        back_populates="feedback",
        cascade="all, delete-orphan",
        order_by="FeedbackScreenshot.sort_order",
    )


class FeedbackScreenshot(Base):
    __tablename__ = "feedback_screenshots"
    __table_args__ = (
        Index("idx_feedback_screenshots_feedback_order", "feedback_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feedback_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("feedbacks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    feedback = relationship("Feedback", back_populates="screenshots")
    asset = relationship("MediaAsset", foreign_keys=[asset_id])
