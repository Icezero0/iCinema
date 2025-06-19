from typing import Dict, Set, Optional
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import logging
import asyncio

# 导入CRUD操作和数据库会话
from app import crud
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

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
        # 存储活跃房间的用户集合 room_id -> {user_id1, user_id2, ...}
        self.active_room_users: Dict[int, Set[int]] = {}

    async def register_connection(self, websocket: WebSocket, user_id: int):
        """注册WebSocket连接"""
        self.connections[user_id] = websocket
        logger.info(f"User {user_id} registered in connection manager")

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
        rooms_to_remove = []
        for room_id in list(self.active_room_users.keys()):
            if user_id in self.active_room_users[room_id]:
                self.active_room_users[room_id].discard(user_id)
                # 如果房间没有在线用户了，标记为需要移除
                if not self.active_room_users[room_id]:
                    rooms_to_remove.append(room_id)
        
        # 移除空房间并更新数据库状态
        for room_id in rooms_to_remove:
            del self.active_room_users[room_id]
            # 异步更新房间状态
            asyncio.create_task(self._update_room_status(room_id, False))
            logger.info(f"Room {room_id} became inactive")
            
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def _update_room_status(self, room_id: int, is_active: bool):
        """更新房间活跃状态到数据库"""
        try:
            async with AsyncSessionLocal() as db:  # type: ignore
                await crud.rooms.update_room_active_status(db, room_id, is_active)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update room {room_id} status to {is_active}: {e}")

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

    async def enter_room(self, user_id: int, room_id: int) -> bool:
        """用户进入房间（当用户打开房间页面时调用）"""
        try:
            async with AsyncSessionLocal() as db:  # type: ignore
                # 检查房间是否存在
                room = await crud.rooms.get_room(db, room_id)
                if not room:
                    logger.warning(f"User {user_id} tried to enter non-existent room {room_id}")
                    return False
                
                # 检查用户是否为房间成员
                if not await crud.rooms.is_room_member(db, room_id, user_id):
                    logger.warning(f"User {user_id} is not a member of room {room_id}")
                    return False
                
                # 检查房间是否是新激活的
                was_empty = room_id not in self.active_room_users or len(self.active_room_users[room_id]) == 0
                
                if room_id not in self.active_room_users:
                    self.active_room_users[room_id] = set()
                    
                self.active_room_users[room_id].add(user_id)
                
                # 如果房间从空变为非空，更新数据库状态
                if was_empty:
                    await crud.rooms.update_room_active_status(db, room_id, True)
                    await db.commit()
                    logger.info(f"Room {room_id} became active")
                
                logger.info(f"User {user_id} entered room {room_id}")
                return True
                
        except Exception as e:
            logger.error(f"User {user_id} failed to enter room {room_id}: {e}")
            return False

    async def leave_room(self, user_id: int, room_id: int):
        """用户离开房间"""
        if room_id in self.active_room_users:
            self.active_room_users[room_id].discard(user_id)
            
            # 如果房间变空了，清理并更新数据库状态
            if not self.active_room_users[room_id]:
                del self.active_room_users[room_id]
                # 异步更新房间状态
                asyncio.create_task(self._update_room_status(room_id, False))
                logger.info(f"Room {room_id} became inactive")
                
        logger.info(f"User {user_id} left room {room_id}")

    async def broadcast_to_room(self, room_id: int, message: dict, exclude_user: Optional[int] = None) -> int:
        
        """广播消息到房间所有在线成员"""
        if room_id not in self.active_room_users:
            return 0
        sent_count = 0
        for user_id in self.active_room_users[room_id].copy():
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
        return len(self.active_room_users.get(room_id, set()))
        
    def get_active_rooms_count(self) -> int:
        """获取活跃房间数量"""
        return len(self.active_room_users)
        
    def get_room_active_users(self, room_id: int) -> Set[int]:
        """获取房间的活跃用户列表"""
        return self.active_room_users.get(room_id, set()).copy()
        
    def is_room_active(self, room_id: int) -> bool:
        """检查房间是否活跃（有在线用户）"""
        return room_id in self.active_room_users and len(self.active_room_users[room_id]) > 0
    
    def is_online_user(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.connections
    
    def get_user_current_room(self, user_id: int) -> Optional[int]:
        """获取用户当前所在的房间ID"""
        for room_id, users in self.active_room_users.items():
            if user_id in users:
                return room_id
        return None

# 全局连接管理器实例
manager = ConnectionManager()
