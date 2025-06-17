from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import schemas, crud
from ..database import get_db
from app.auth.dependencies import get_current_user
from app.websocket.manager import manager
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/rooms/{room_id}/messages/")
async def create_message(
    room_id: int,
    message: schemas.MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """
    在指定房间中创建新消息
    """
    # 检查房间是否存在
    db_room = await crud.rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="房间不存在"
        )
    room = schemas.Room.model_validate(db_room)
    
    # 检查用户是否有权限在该房间发送消息
    # 用户必须是房主或房间成员
    if (current_user.id != room.owner_id) and not await crud.rooms.is_room_member(db, room_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该房间的成员，无权发送消息"
        )
    
    # 创建消息并保存到数据库
    db_message = await crud.messages.create_message(
        db=db,
        message=message,
        room_id=room_id,
        user_id=current_user.id
    )
    
    # 提交数据库事务
    await db.commit()
    await db.refresh(db_message)
    
    # 通过 WebSocket 广播消息给房间内的其他用户
    try:
        # 构造 WebSocket 广播消息
        timestamp = datetime.now(timezone.utc).isoformat()
        ws_message = {
            "type": "room_message",
            "payload": {
                "room_id": room_id,
                "sender_id": current_user.id,
                "content": message.content,
                "timestamp": timestamp
            }
        }
        
        # 向房间内除发送者外的所有在线用户广播
        sent_count = await manager.broadcast_to_room(room_id, ws_message, exclude_user=current_user.id)
        
        return {
            "message": "消息发送成功",
            "message_id": db_message.id,
            "sent_to_online_users": sent_count,
            "timestamp": timestamp
        }
        
    except Exception as e:
        # WebSocket 广播失败不应该影响消息保存
        logger.error(f"Failed to broadcast message {db_message.id}: {e}")
        return {
            "message": "消息已保存，但广播失败",
            "message_id": db_message.id,
            "sent_to_online_users": 0,
            "timestamp": timestamp
        }

@router.get("/rooms/{room_id}/messages/", response_model=schemas.MessageListResponse)
async def get_room_messages(
    room_id: int,
    skip: int = Query(0, ge=0, description="跳过的消息数量"),
    limit: int = Query(20, ge=1, le=100, description="返回的消息数量"),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """
    获取指定房间的消息列表
    """
    # 检查房间是否存在
    db_room = await crud.rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="房间不存在"
        )
    room = schemas.Room.model_validate(db_room)
    
    # 检查用户是否有权限在该房间发送消息
    # 用户必须是房主或房间成员
    if (current_user.id != room.owner_id) and not await crud.rooms.is_room_member(db, room_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该房间的成员，无法查看消息"
        )
    
    # 获取消息列表
    db_messages, total = await crud.messages.get_room_messages(
        db=db,
        room_id=room_id,
        skip=skip,
        limit=limit
    )
    
    # 转换为schema格式
    messages = [
        schemas.MessageResponse.model_validate(message) for message in db_messages
    ]
    
    return schemas.MessageListResponse(
        items=messages,
        total=total
    )

@router.get("/messages/{message_id}", response_model=schemas.MessageResponse)
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """
    获取指定消息的详细信息
    """
    # 获取消息
    db_message = await crud.messages.get_message(db, message_id)
    if not db_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    return schemas.MessageResponse.model_validate(db_message)

