from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# 用户相关的 Schema
    
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    avatar_path: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class UserUpdate(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    username: Optional[str] = None
    avatar_base64: Optional[str] = None

# 房间相关的 Schema
class RoomBase(BaseModel):
    name: str

class RoomCreate(RoomBase):
    pass

class Room(RoomBase):
    id: int
    created_at: datetime
    owner: User
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
    rooms_joined: List[Room] = []

class RoomResponse(Room):
    owner: User
    messages: List[Message] = []
    members: List[User] = []