import enum
from sqlalchemy import Column, Enum, Integer, String, DateTime, ForeignKey, Boolean, Table, Sequence
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
from datetime import timezone

class UserType(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"

# 创建房间成员关系的中间表
room_members = Table(
    "room_members",
    Base.metadata,
    Column("room_id", Integer, ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), default=datetime.now(timezone.utc)),
    Column("user_type", Enum(UserType), default=UserType.MEMBER, nullable=False),
)

def get_utc_now():
    """获取当前UTC时间的辅助函数"""
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, Sequence('user_id_seq', start=10000, increment=1),
               primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    avatar_path = Column(String, nullable=True, default=None)
    
    rooms_owned = relationship("Room", back_populates="owner")
    messages = relationship("Message", back_populates="user")
    received_notifications = relationship("Notification", foreign_keys="Notification.recipient_id", back_populates="recipient")
    sent_notifications = relationship("Notification", foreign_keys="Notification.sender_id", back_populates="sender")
    
    rooms_joined = relationship(
        "Room",
        secondary=room_members,
        back_populates="members"
    )

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, Sequence('room_id_seq', start=10000, increment=1),
               primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    
    owner = relationship("User", back_populates="rooms_owned")
    messages = relationship("Message", back_populates="room")
    
    members = relationship(
        "User",
        secondary=room_members,
        back_populates="rooms_joined"
    )

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    # 用户删除时设置为NULL（匿名消息）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # 房间删除时级联删除消息
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    
    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(String, nullable=False)
    status = Column(String, nullable=False, default="unread")
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    is_deleted = Column(Boolean, default=False, nullable=False)

    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_notifications")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_notifications")