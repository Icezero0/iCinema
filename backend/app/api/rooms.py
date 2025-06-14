import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from .. import schemas, crud
from ..database import get_db
from .users import get_current_user
from ..utils.notifications import create_notification_content 

router = APIRouter()

@router.post("/rooms/", response_model=schemas.RoomResponse)
async def create_room(
    room: schemas.RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    print(f"Creating room with data: {room}")
    # 创建房间，房主为当前用户
    db_room = await crud.rooms.create_room(db, room, owner_id=current_user.id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="房间创建失败")
    
    schema_room = schemas.Room.model_validate(db_room)

    return schemas.RoomResponse(
        id=schema_room.id,
        owner_id=current_user.id,
        name=room.name,
        created_at=schema_room.created_at,
        is_active=True
    )

@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 删除房间（仅房主可操作）
    db_room = await crud.rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    if db_room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    
    success = await crud.rooms.delete_room(db, room_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="删除房间失败")
    
    return None  # 204状态码不需要返回内容

@router.get("/rooms/{room_id}", response_model=schemas.RoomResponse)
async def get_room_info(
    room_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 查询房间信息
    db_room = await crud.rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    
    schema_room = schemas.Room.model_validate(db_room)

    return schemas.RoomResponse(
        id=schema_room.id,
        name=schema_room.name,
        created_at=schema_room.created_at,
        owner_id=schema_room.owner_id,
        is_active=True,
    )

@router.get("/rooms/{room_id}/details", response_model=schemas.RoomDetailsResponse)
async def get_room_details(
    room_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 查询房间信息（详细）
    db_room = await crud.rooms.get_room_details(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    return db_room

@router.put("/rooms/{room_id}", response_model=schemas.Room)
async def update_room(
    room_id: int,
    room_update: schemas.RoomUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 更新房间信息（仅房主可操作）
    db_room = await crud.rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    if db_room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    update_data = room_update.model_dump(exclude_unset=True)
    updated_room = await crud.rooms.update_room(db, room_id, update_data)
    return updated_room

@router.post("/rooms/{room_id}/members", status_code=status.HTTP_200_OK)
async def create_room_invitation(
    room_id: int,
    roomMemberAdd: schemas.RoomMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    将用户添加为房间成员
    - 如果邀请者是房主，直接添加用户到房间
    - 如果邀请者不是房主，创建一条通知记录（待实现）
    """
    # 1. 获取房间信息
    db_room = await crud.rooms.get_room_details(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    
    # 2. 检查用户是否存在
    db_user = await crud.users.get_user(db, user_id=roomMemberAdd.user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    schema_room = schemas.Room.model_validate(db_room)
    schema_user = schemas.User.model_validate(db_user)
    
    # 3. 检查用户是否已在房间中
    if await crud.rooms.is_room_member(db, room_id=room_id,user_id=roomMemberAdd.user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已在房间中")
    
    # 4. 检查用户是否是房主
    if schema_room.owner_id == schema_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="房主不能被添加为成员")
    
    # action类型决定操作类型
    if roomMemberAdd.action == "owner_invitation":
        # 验证当前用户是否为房主
        if schema_room.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="并非房主"
            )
        
        # 创建用于邀请加入的通知记录
        await crud.notifications.create_notification(
            db=db,
            content=create_notification_content(
                room_id=room_id,
                user_id=roomMemberAdd.user_id,
                type="owner_invitation"
            ),
            recipient_id=roomMemberAdd.user_id,
            sender_id=current_user.id, 
            status="pending"  # 邀请状态为待处理
        )
        #TODO :若该用户在线则通过websocket连接推送消息提醒查看
        return {"message": "已发送邀请给用户", "status": "pending"}
    
    elif roomMemberAdd.action == "join_request":
        # 用户请求加入房间
        
        # 创建用于申请加入的通知记录
        await crud.notifications.create_notification(
            db=db,
            content=create_notification_content(
                room_id=room_id,
                user_id=roomMemberAdd.user_id,
                type="join_request"
            ),
            recipient_id=schema_room.owner_id,
            sender_id=current_user.id,
            status="pending"  # 邀请状态为待处理
        )
        #TODO :若房主在线则通过websocket连接推送消息提醒查看
        return {"message": "已发送加入申请", "status": "pending"}
    
    elif roomMemberAdd.action == "member_invitation":
        # 邀请其他用户加入
        # 验证当前用户是否为房间成员

        if (current_user.id == schema_room.owner_id) or (
        not await crud.rooms.is_room_member(db, room_id=room_id,user_id=current_user.id)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="只有房间成员可以邀请其他用户"
            )
        
        # 创建用于邀请加入的通知记录
        await crud.notifications.create_notification(
            db=db,
            content=create_notification_content(
                room_id=room_id,
                user_id=roomMemberAdd.user_id,
                type="member_invitation"
            ),
            recipient_id=roomMemberAdd.user_id,
            sender_id=current_user.id,
            status="pending"  # 邀请状态为待处理
        )
        #TODO :若该用户在线则通过websocket连接推送消息提醒查看
        return {"message": "已发送邀请给用户", "status": "pending"}
    
    else:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Unknown action"
            )

@router.delete("/rooms/{room_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_room_member(
    room_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 获取房间信息
    db_room = await crud.rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    # 权限校验：房主或本人
    if current_user.id != user_id and current_user.id != db_room.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限移除该成员")
    # 不允许移除房主
    if user_id == db_room.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除房主")
    # 移除成员
    success = await crud.rooms.remove_room_member(db, room_id, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="移除成员失败")
    return None