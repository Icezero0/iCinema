from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import schemas
from ..database import get_db
from .users import get_current_user
from ..crud import rooms as crud_rooms

router = APIRouter()

@router.post("/rooms/", response_model=schemas.RoomResponse)
async def create_room(
    room: schemas.RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    print(f"Creating room with data: {room}")
    # 创建房间，房主为当前用户
    db_room = await crud_rooms.create_room(db, room, owner_id=current_user.id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="房间创建失败")
    return schemas.RoomResponse(
        id=db_room.id,  #type: ignore
        name=room.name,
        created_at=db_room.created_at,  #type: ignore
        owner=current_user,
        is_active=True,
        messages=[],
        members=[]
    )

@router.get("/rooms/{room_id}", response_model=schemas.RoomResponse)
async def get_room_info(
    room_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 查询房间自身信息（不含成员）
    db_room = await crud_rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    return schemas.RoomResponse(
        id=db_room.id,  #type: ignore
        name=db_room.name,  #type: ignore
        created_at=db_room.created_at,  #type: ignore
        owner=db_room.owner,
        is_active=True,
        messages=[],
        members=[]
    )

@router.get("/rooms/{room_id}/details", response_model=schemas.RoomResponse)
async def get_room_details(
    room_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 查询房间信息（含成员）
    db_room = await crud_rooms.get_room_details(db, room_id)
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
    db_room = await crud_rooms.get_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
    if db_room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    update_data = room_update.model_dump(exclude_unset=True)
    updated_room = await crud_rooms.update_room(db, room_id, update_data)
    return updated_room
