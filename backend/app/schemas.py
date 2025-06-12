from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# 用户相关的 Schema
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    icon_path: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class UserUpdate(UserBase):
    icon_path: Optional[str] = None

# 房间相关的 Schema
class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    pass

class Room(RoomBase):
    id: int
    created_at: datetime
    owner_id: int
    is_active: bool = True
    members: List[User] = []

    model_config = {
        "from_attributes": True
    }

# 消息相关的 Schema
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    room_id: int

class Message(MessageBase):
    id: int
    created_at: datetime
    user_id: int
    room_id: int
    user: User
    
    model_config = {
        "from_attributes": True
    }

# 响应模型
class UserResponse(User):
    rooms_owned: List[Room] = []
    joined_rooms: List[Room] = []
    messages: List[Message] = []

class RoomResponse(Room):
    owner: User
    messages: List[Message] = []
    members: List[User] = []