from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# 用户相关的 Schema

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
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

class Room(RoomCreate):
    id: int
    owner_id: int
    created_at: datetime
    is_active: bool
    
    model_config = {
        "from_attributes": True
    }

class RoomUpdate(BaseModel):
    name: Optional[str] = None

class RoomList(BaseModel):
    items: List[Room]
    total: int

# 房间成员相关的 Schema
class RoomMemberAdd(BaseModel):
    user_id: int  # 要添加的用户ID
    action: str

# 消息相关的 Schema
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    created_at: datetime
    user_id: Optional[int] = None
    room_id: int
    
    model_config = {
        "from_attributes": True
    }

# 用户通知相关的 Schema

class NotificationBase(BaseModel):
    content: str

class NotificationCreate(NotificationBase):
    recipient_id: int
    sender_id: Optional[int] = None
    status: Optional[str] = None

class Notification(NotificationCreate):
    id: int
    created_at: datetime
    status: str = ""
    is_deleted: bool = False

    model_config = {
        "from_attributes": True
    }

class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    is_deleted: Optional[bool] = None

class NotificationList(BaseModel):
    items: List[Notification]
    total: int

class NotificationAction(BaseModel):
    action: str  # "accept" or "reject"
    token: Optional[str] = None  # 用于验证请求的令牌

# 用于通知确认的请求模型
class NotificationConfirm(BaseModel):
    notification_id: int
    type : str
    token: str

# 响应模型
class UserResponse(User):
    pass

    model_config = {
        "from_attributes": True
    }

class UserDetailsResponse(User):
    rooms_owned: RoomList
    rooms_joined: RoomList

    model_config = {
        "from_attributes": True
    }


class RoomResponse(Room):
    pass

    model_config = {
        "from_attributes": True
    }

class RoomDetailsResponse(Room):
    owner : User
    members : List[User]
    # messages : List[]

    model_config = {
        "from_attributes": True
    }


class RoomListResponse(RoomList):
    pass

    model_config = {
        "from_attributes": True
    }

class UserRoomsListResponse(BaseModel):
    rooms_owned: List[RoomList]
    rooms_joined: List[RoomList]
    
    model_config = {
        "from_attributes": True
    }

class NotificationResponse(Notification):
    created_at: datetime
    is_deleted: bool = False
    
    model_config = {
        "from_attributes": True
    }

class NotificationListResponse(NotificationList):
    pass
    
    model_config = {
        "from_attributes": True
    }

class MessageResponse(MessageBase):
    id: int
    created_at: datetime
    user_id: Optional[int] = None
    
    model_config = {
        "from_attributes": True
    }

class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int

    


