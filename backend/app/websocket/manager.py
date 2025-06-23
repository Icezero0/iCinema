from typing import Dict, Set, Optional
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging
import asyncio

# 导入CRUD操作和数据库会话
from app import crud
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

@dataclass
class ActiveRoom:
    """活跃房间状态类 - 仅存储数据，不包含计算逻辑"""
    # 用户管理
    online_users: Set[int] = field(default_factory=set)
    
    # 视频基础信息
    video_url: Optional[str] = None
    video_duration: Optional[float] = None
    
    # 最后操作快照（供前端计算使用）
    last_operation_type: Optional[str] = None      # "play", "pause", "seek", "set_url"
    last_operation_time: Optional[datetime] = None # 操作时间戳
    last_operation_progress: float = 0.0           # 操作时的进度
    last_operation_user: Optional[int] = None      # 操作用户
    last_operation_params: Optional[Dict] = None   # 操作参数
    
    # 房间元数据
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        """转换为字典格式，用于发送给前端"""
        return {
            "online_users_count": len(self.online_users),
            "video_url": self.video_url,
            "video_duration": self.video_duration,
            "last_operation_type": self.last_operation_type,
            "last_operation_time": self.last_operation_time.isoformat() if self.last_operation_time else None,
            "last_operation_progress": self.last_operation_progress,
            "last_operation_user": self.last_operation_user,
            "last_operation_params": self.last_operation_params
        }
    
    def update_operation(self, operation_type: str, user_id: int, progress: float = 0.0, params: Optional[Dict] = None):
        """更新操作记录"""
        self.last_operation_type = operation_type
        self.last_operation_time = datetime.now(timezone.utc)
        self.last_operation_progress = progress
        self.last_operation_user = user_id
        self.last_operation_params = params or {}
        self.last_activity = self.last_operation_time

class ConnectionManager:
    """
    WebSocket连接管理器
    
    职责：
    - 管理用户连接映射
    - 管理房间成员关系  
    - 提供消息发送功能
    - 不处理WebSocket协议层操作（如accept）
    """
    def __init__(self):
        # 存储用户连接
        self.connections: Dict[int, WebSocket] = {}
        # 存储活跃房间对象 room_id -> ActiveRoom
        self.active_rooms: Dict[int, ActiveRoom] = {}
        # 房间停用定时器 room_id -> asyncio.Task
        self.room_deactivation_timers: Dict[int, asyncio.Task] = {}
        # 房间停用延迟时间（秒）- 5分钟
        self.ROOM_DEACTIVATION_DELAY = 300

    async def register_connection(self, websocket: WebSocket, user_id: int):
        """注册WebSocket连接"""
        self.connections[user_id] = websocket
        logger.info(f"User {user_id} registered in connection manager")

    def get_or_create_room(self, room_id: int) -> ActiveRoom:
        """获取或创建房间对象"""
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = ActiveRoom()
        return self.active_rooms[room_id]
    
    def update_room_video_operation(self, room_id: int, operation_type: str, user_id: int, 
                                   progress: float = 0.0, **kwargs):
        """更新房间视频操作"""
        room = self.get_or_create_room(room_id)
        
        # 处理特殊操作类型
        if operation_type == "set_url":
            room.video_url = kwargs.get("url")
            room.video_duration = kwargs.get("duration")
        
        # 记录操作
        room.update_operation(operation_type, user_id, progress, kwargs)
    
    def get_room_info(self, room_id: int) -> Optional[Dict]:
        """获取房间信息（用于发送给前端）"""
        if room_id in self.active_rooms:
            return self.active_rooms[room_id].to_dict()
        return None

    # async def connect(self, websocket: WebSocket, user_id: int, auto_accept: bool = True):
    #     """建立WebSocket连接（包含accept操作）- 向后兼容方法"""
    #     if auto_accept:
    #         try:
    #             await websocket.accept()
    #         except RuntimeError as e:
    #             # 连接已经被accept，继续注册
    #             logger.warning(f"WebSocket already accepted for user {user_id}: {e}")
        
    #     await self.register_connection(websocket, user_id)

    def disconnect(self, user_id: int):
        """断开WebSocket连接"""
        self.connections.pop(user_id, None)
        
        # 从所有活跃房间中移除用户
        rooms_to_check = []
        for room_id in list(self.active_rooms.keys()):
            room = self.active_rooms[room_id]
            if user_id in room.online_users:
                room.online_users.discard(user_id)
                # 如果房间没有在线用户了，标记为需要检查
                if not room.online_users:
                    rooms_to_check.append(room_id)
        
        # 对于变空的房间，保留在字典中但清空用户集合，表示延迟停用状态
        for room_id in rooms_to_check:
            # 房间对象保持在字典中，但用户集合为空，表示正在延迟停用
            # 启动延迟停用定时器
            asyncio.create_task(self._schedule_room_deactivation(room_id))
            logger.info(f"Room {room_id} entered delayed deactivation state (empty but in dict)")
            
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def _update_room_status(self, room_id: int, is_active: bool):
        """更新房间活跃状态到数据库"""
        try:
            async with AsyncSessionLocal() as db:  # type: ignore
                await crud.rooms.update_room_active_status(db, room_id, is_active)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update room {room_id} status to {is_active}: {e}")

    async def _schedule_room_deactivation(self, room_id: int):
        """调度房间停用任务"""
        # 如果已有定时器，先取消
        if room_id in self.room_deactivation_timers:
            self.room_deactivation_timers[room_id].cancel()
        
        # 创建新的定时器
        timer = asyncio.create_task(self._delayed_room_deactivation(room_id))
        self.room_deactivation_timers[room_id] = timer
        logger.info(f"Room {room_id} scheduled for deactivation in {self.ROOM_DEACTIVATION_DELAY}s")

    async def _delayed_room_deactivation(self, room_id: int):
        """延迟房间停用执行函数"""
        try:
            await asyncio.sleep(self.ROOM_DEACTIVATION_DELAY)
            # 再次检查房间是否真的为空（用户集合为空）
            if room_id in self.active_rooms and len(self.active_rooms[room_id].online_users) == 0:
                # 真正停用：从字典中删除房间
                del self.active_rooms[room_id]
                await self._update_room_status(room_id, False)
                logger.info(f"Room {room_id} truly deactivated after {self.ROOM_DEACTIVATION_DELAY}s delay (removed from dict)")
            elif room_id in self.active_rooms and len(self.active_rooms[room_id].online_users) > 0:
                logger.info(f"Room {room_id} deactivation cancelled - users rejoined")
            else:
                logger.info(f"Room {room_id} was already removed from dict")
            # 清理定时器记录
            self.room_deactivation_timers.pop(room_id, None)
        except asyncio.CancelledError:
            logger.info(f"Room {room_id} deactivation timer cancelled")
            self.room_deactivation_timers.pop(room_id, None)
        except Exception as e:
            logger.error(f"Error during delayed deactivation of room {room_id}: {e}")
            self.room_deactivation_timers.pop(room_id, None)

    def _cancel_room_deactivation(self, room_id: int):
        """取消房间停用定时器"""
        if room_id in self.room_deactivation_timers:
            self.room_deactivation_timers[room_id].cancel()
            self.room_deactivation_timers.pop(room_id, None)
            logger.info(f"Room {room_id} deactivation timer cancelled")

    async def send_to_user(self, user_id: int, message: dict) -> bool:
        """发送消息给特定用户"""
        if user_id in self.connections:
            try:
                websocket = self.connections[user_id]
                await websocket.send_json(message)
                print(f"Sent message to user {user_id}: {message}")
                return True
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                self.disconnect(user_id)
                return False
        return False

    async def enter_room(self, user_id: int, room_id: int) -> Dict:
        """用户进入房间（当用户打开房间页面时调用）"""
        try:
            async with AsyncSessionLocal() as db:  # type: ignore
                # 检查房间是否存在
                room_db = await crud.rooms.get_room(db, room_id)
                if not room_db:
                    logger.warning(f"User {user_id} tried to enter non-existent room {room_id}")
                    return {"success": False, "error": "房间不存在"}
                
                # 检查用户是否为房间成员
                if not await crud.rooms.is_room_member(db, room_id, user_id):
                    logger.warning(f"User {user_id} is not a member of room {room_id}")
                    return {"success": False, "error": "无权限访问该房间"}
                
                # 获取或创建房间对象
                room = self.get_or_create_room(room_id)
                
                # 检查房间是否是新激活的
                was_empty = len(room.online_users) == 0
                
                # 如果房间之前为空，取消可能存在的停用定时器
                if was_empty:
                    self._cancel_room_deactivation(room_id)
                
                # 添加用户到房间
                room.online_users.add(user_id)
                room.last_activity = datetime.now(timezone.utc)
                
                # 如果房间从空变为非空，更新数据库状态
                if was_empty:
                    await crud.rooms.update_room_active_status(db, room_id, True)
                    await db.commit()
                    logger.info(f"Room {room_id} became active")
                
                logger.info(f"User {user_id} entered room {room_id}")
                
                # 返回成功状态和房间信息
                return {
                    "success": True, 
                    "room_info": room.to_dict()
                }
                
        except Exception as e:
            logger.error(f"User {user_id} failed to enter room {room_id}: {e}")
            return {"success": False, "error": "进入房间时发生错误"}

    async def leave_room(self, user_id: int, room_id: int):
        """用户离开房间"""
        if room_id in self.active_rooms:
            room = self.active_rooms[room_id]
            room.online_users.discard(user_id)
            
            # 如果房间变空了，保留在字典中但启动延迟停用定时器
            if not room.online_users:
                # 保持房间在字典中，用户集合为空表示正在延迟停用
                await self._schedule_room_deactivation(room_id)
                logger.info(f"Room {room_id} entered delayed deactivation state (empty but in dict)")
                
        logger.info(f"User {user_id} left room {room_id}")

    async def broadcast_to_room(self, room_id: int, message: dict, exclude_user: Optional[int] = None) -> int:
        """广播消息到房间所有在线成员"""
        if room_id not in self.active_rooms:
            return 0
        
        room = self.active_rooms[room_id]
        sent_count = 0
        for user_id in room.online_users.copy():
            if user_id != exclude_user:
                if await self.send_to_user(user_id, message):
                    sent_count += 1
        
        logger.info(f"Broadcast to room {room_id}, sent to {sent_count} users")
        return sent_count

    async def send_room_message(self, sender_id: int, room_id: int, message_content: str) -> Optional[int]:
        """发送消息到房间（从API调用）"""
        try:
                timestamp = datetime.now(timezone.utc).isoformat()
                
                ws_message = {
                    "type": "room_message",
                    "payload": {
                        "room_id": room_id,
                        "sender_id": sender_id,
                        "content": message_content,
                        "timestamp": timestamp
                    }
                }
                
                # 向房间内除发送者外的所有在线用户推送消息
                sent_count = await self.broadcast_to_room(room_id, ws_message, exclude_user=sender_id)
                print('here')
                
                logger.info(f"Message from user {sender_id} sent to room {room_id}, reached {sent_count} users")
                return sent_count
                
        except Exception as e:
            logger.error(f"Failed to send message from user {sender_id} to room {room_id}: {e}")
            return None

    def get_online_users_count(self) -> int:
        """获取在线用户数量"""
        return len(self.connections)

    def get_room_active_users_count(self, room_id: int) -> int:
        """获取房间活跃用户数量"""
        if room_id in self.active_rooms:
            return len(self.active_rooms[room_id].online_users)
        return 0
        
    def get_active_rooms_count(self) -> int:
        """获取活跃房间数量（包括延迟停用中的房间）"""
        return len(self.active_rooms)
        
    def get_truly_active_rooms_count(self) -> int:
        """获取真正活跃的房间数量（不包括延迟停用中的房间）"""
        return len([room_id for room_id, room in self.active_rooms.items() if len(room.online_users) > 0])
        
    def get_room_active_users(self, room_id: int) -> Set[int]:
        """获取房间的活跃用户列表"""
        if room_id in self.active_rooms:
            return self.active_rooms[room_id].online_users.copy()
        return set()
        
    def is_room_active(self, room_id: int) -> bool:
        """检查房间是否活跃（有在线用户）"""
        return room_id in self.active_rooms and len(self.active_rooms[room_id].online_users) > 0
    
    def is_room_in_delayed_deactivation(self, room_id: int) -> bool:
        """检查房间是否处于延迟停用状态"""
        return room_id in self.active_rooms and len(self.active_rooms[room_id].online_users) == 0
    
    def is_room_deactivated(self, room_id: int) -> bool:
        """检查房间是否已完全停用"""
        return room_id not in self.active_rooms
    
    def get_room_status(self, room_id: int) -> str:
        """获取房间状态描述"""
        if room_id not in self.active_rooms:
            return "deactivated"
        elif len(self.active_rooms[room_id].online_users) == 0:
            return "delayed_deactivation"
        else:
            return "active"
    
    def is_online_user(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.connections
    
    def get_user_current_room(self, user_id: int) -> Optional[int]:
        """获取用户当前所在的房间ID"""
        for room_id, room in self.active_rooms.items():
            if user_id in room.online_users:
                return room_id
        return None

    async def shutdown(self):
        """优雅关闭：取消所有房间停用定时器"""
        logger.info("Shutting down connection manager, cancelling all deactivation timers")
        for room_id, timer in list(self.room_deactivation_timers.items()):
            timer.cancel()
            logger.info(f"Cancelled deactivation timer for room {room_id}")
        
        # 等待所有定时器完成取消
        if self.room_deactivation_timers:
            await asyncio.gather(
                *self.room_deactivation_timers.values(), 
                return_exceptions=True
            )
        self.room_deactivation_timers.clear()

# 全局连接管理器实例
manager = ConnectionManager()
