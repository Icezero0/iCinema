import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.websocket.manager import manager
from .. import schemas, crud, models
from ..database import get_db
from app.auth import dependencies as auth_deps
from ..utils.notifications import create_notification_content 

router = APIRouter()

@router.post("/rooms", response_model=schemas.RoomResponse)
async def create_room(
    room: schemas.RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(auth_deps.get_current_user)
):
    db_room = await crud.rooms.create_room(db, room, owner_id=current_user.id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="房间创建失败")
    
    schema_room = schemas.Room.model_validate(db_room)

    return schemas.RoomResponse(
        id=schema_room.id,
        owner_id=current_user.id,
        name=room.name,
        created_at=schema_room.created_at,
        is_active=True,
        is_public=schema_room.is_public,
        config=schema_room.config
    )

@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(auth_deps.get_current_user)
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
        is_public=schema_room.is_public
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
    message_count = await crud.rooms.get_room_message_count(db, room_id)
    # 组装响应
    room_schema = schemas.RoomDetailsResponse.model_validate(db_room, from_attributes=True)
    room_schema.message_count = message_count
    return room_schema

@router.put("/rooms/{room_id}", response_model=schemas.Room)
async def update_room(
    room_id: int,
    room_update: schemas.RoomUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(auth_deps.get_current_user)
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
    current_user = Depends(auth_deps.get_current_user)
):
    """
    将用户添加为房间成员
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
        if manager.is_online_user(roomMemberAdd.user_id):
            # 如果用户在线，则通过WebSocket推送消息提醒
            await manager.send_to_user(
                roomMemberAdd.user_id,{
                    "type": "receive_notification"
                }
            )
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
        if manager.is_online_user(schema_room.owner_id):
            # 如果用户在线，则通过WebSocket推送消息提醒
            await manager.send_to_user(
                schema_room.owner_id,{
                    "type": "receive_notification"
                }
            )
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
        if manager.is_online_user(roomMemberAdd.user_id):
            # 如果用户在线，则通过WebSocket推送消息提醒
            await manager.send_to_user(
                roomMemberAdd.user_id,{
                    "type": "receive_notification"
                }
            )
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
    current_user = Depends(auth_deps.get_current_user)
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
    
    # 校验：该用户必须在房间内
    is_member = await crud.rooms.is_room_member(db, room_id, user_id)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户不在房间内")
    # 移除成员
    success = await crud.rooms.remove_room_member(db, room_id, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="移除成员失败")
    return None

@router.get("/rooms", response_model=schemas.RoomList)
async def list_rooms(
    skip: int = Query(0, ge=0, description="分页起始位置"),
    limit: int = Query(20, ge=1, le=100, description="分页数量"),
    name: str = Query(None, description="房间名模糊搜索"),
    owner_id: int = Query(None, description="房主ID"),
    is_active: bool = Query(None, description="是否活跃"),
    is_public: bool = Query(None, description="是否公开房间"),
    db: AsyncSession = Depends(get_db)
):
    """
    分页获取房间列表，支持按名称、房主、活跃状态筛选。
    """
    rooms, total = await crud.rooms.get_rooms_by_filter(
        db=db,
        name=name,
        owner_id=owner_id,
        is_active=is_active,
        is_public=is_public,
        skip=skip,
        limit=limit
    )
    items = [schemas.Room.model_validate(room, from_attributes=True) for room in rooms]
    return schemas.RoomList(items=items, total=total)

@router.get("/users/me/room_ids", response_model=List[int])
async def get_my_room_ids(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(auth_deps.get_current_user)
):
    """
    查询当前用户所在的所有房间id（包括拥有和加入的房间）
    """
    # 获取拥有的房间id
    owned_query = select(models.Room.id).where(models.Room.owner_id == current_user.id)
    owned_result = await db.execute(owned_query)
    owned_ids = set(owned_result.scalars().all())

    # 获取加入的房间id
    joined_query = select(models.room_members.c.room_id).where(models.room_members.c.user_id == current_user.id)
    joined_result = await db.execute(joined_query)
    joined_ids = set(joined_result.scalars().all())

    all_ids = list(owned_ids | joined_ids)
    return all_ids

@router.get("/users/{user_id}/rooms", response_model=schemas.RoomList)
async def get_user_rooms_by_member(
    user_id: int,
    skip: int = Query(0, ge=0, description="分页起始位置"),
    limit: int = Query(10, ge=1, le=100, description="分页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    查询用户作为成员（包括owner和member）关联的房间，支持分页
    """
    from ..models import room_members, Room, UserType
    # 查找room_members表中user_id匹配的所有房间id
    result = await db.execute(
        select(Room)
        .join(room_members, Room.id == room_members.c.room_id)
        .where(room_members.c.user_id == user_id)
        .order_by(Room.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rooms = result.scalars().all()
    # 统计总数
    count_result = await db.execute(
        select(func.count()).select_from(room_members).where(room_members.c.user_id == user_id)
    )
    total = count_result.scalar_one()
    items = [schemas.Room.model_validate(room, from_attributes=True) for room in rooms]
    return schemas.RoomList(items=items, total=total)