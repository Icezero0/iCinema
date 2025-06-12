from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
from datetime import timezone

# 创建房间成员关系的中间表
room_members = Table(
    "room_members",
    Base.metadata,
    Column("room_id", Integer, ForeignKey("rooms.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), default=datetime.now(timezone.utc)),
)

def get_utc_now():
    """获取当前UTC时间的辅助函数"""
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    avatar_path = Column(String, nullable=True, default=None)
    
    rooms_owned = relationship("Room", back_populates="owner")
    messages = relationship("Message", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    
    rooms_joined = relationship(
        "Room",
        secondary=room_members,
        back_populates="members"
    )

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    status = Column(String, nullable=False, default="unread")
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    user = relationship("User", back_populates="notifications")