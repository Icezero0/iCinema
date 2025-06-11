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
    username = Column(String, unique=True, index=True)  # 用户名应该唯一
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)    # 密码不能为空
    created_at = Column(DateTime(timezone=True), default=get_utc_now)  # 修改这行
    icon_path = Column(String, nullable=True, default=None)  # 存储本地文件路径
    
    # 添加关系
    rooms_owned = relationship("Room", back_populates="owner")
    messages = relationship("Message", back_populates="user")
    
    # 添加成员关系
    joined_rooms = relationship(
        "Room",
        secondary=room_members,
        back_populates="members"
    )

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)   # 房间名不能为空
    created_at = Column(DateTime(timezone=True), default=get_utc_now)  # 修改这行
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)          # 替换 members_id
    
    # 添加关系
    owner = relationship("User", back_populates="rooms_owned")
    messages = relationship("Message", back_populates="room")
    
    # 添加成员关系
    members = relationship(
        "User",
        secondary=room_members,
        back_populates="joined_rooms"
    )

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)  # 修改这行
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    # 添加关系
    user = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")