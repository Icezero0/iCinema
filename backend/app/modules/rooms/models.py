from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.users.models import User

from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomJoinAuditMode,
    RoomJoinRequestAction,
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomVideoSourceType,
    RoomSyncPolicy,
    RoomVisibility,
)


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    visibility: Mapped[RoomVisibility] = mapped_column(
        String(16),
        nullable=False,
        default=RoomVisibility.PRIVATE,
        server_default=RoomVisibility.PRIVATE.value,
        index=True,
    )
    join_audit_mode: Mapped[RoomJoinAuditMode] = mapped_column(
        String(32),
        nullable=False,
        default=RoomJoinAuditMode.MANUAL_REVIEW,
        server_default=RoomJoinAuditMode.MANUAL_REVIEW.value,
        index=True,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])

    members: Mapped[list["RoomMember"]] = relationship(
        "RoomMember",
        back_populates="room",
        cascade="all, delete-orphan",
    )

    settings: Mapped["RoomSettings | None"] = relationship(
        "RoomSettings",
        back_populates="room",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RoomSettings(Base):
    __tablename__ = "room_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    selected_room_video_source_type: Mapped[RoomVideoSourceType] = mapped_column(
        String(32),
        nullable=False,
        default=RoomVideoSourceType.EXTERNAL_URL,
        server_default=RoomVideoSourceType.EXTERNAL_URL.value,
    )
    sync_policy: Mapped[RoomSyncPolicy] = mapped_column(
        String(32),
        nullable=False,
        default=RoomSyncPolicy.AUTO_SYNC,
        server_default=RoomSyncPolicy.AUTO_SYNC.value,
    )
    active_sync_permission: Mapped[RoomActiveSyncPermission] = mapped_column(
        String(32),
        nullable=False,
        default=RoomActiveSyncPermission.OWNER_AND_MANAGER,
        server_default=RoomActiveSyncPermission.OWNER_AND_MANAGER.value,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    room: Mapped["Room"] = relationship(
        "Room",
        back_populates="settings",
    )


class RoomMember(Base):
    __tablename__ = "room_members"

    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)

    room: Mapped["Room"] = relationship("Room", back_populates="members")
    user: Mapped["User"] = relationship("User")


class RoomJoinRequest(Base):
    __tablename__ = "room_join_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    room_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiator_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source: Mapped[RoomJoinRequestSource] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )
    status: Mapped[RoomJoinRequestStatus] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        default=RoomJoinRequestStatus.PENDING,
    )

    room_action: Mapped[RoomJoinRequestAction] = mapped_column(
        String(16),
        nullable=False,
        default=RoomJoinRequestAction.PENDING,
    )

    target_action: Mapped[RoomJoinRequestAction] = mapped_column(
        String(16),
        nullable=False,
        default=RoomJoinRequestAction.PENDING,
    )

    room_action_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    room: Mapped["Room"] = relationship("Room")
    initiator: Mapped["User"] = relationship("User", foreign_keys=[initiator_user_id])
    target: Mapped["User"] = relationship("User", foreign_keys=[target_user_id])
    room_action_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[room_action_by_user_id],
    )
