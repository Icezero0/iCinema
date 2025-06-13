from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models, schemas
from typing import Optional, List
from sqlalchemy.orm import selectinload

async def create_room(
    db: AsyncSession, 
    room: schemas.RoomCreate, 
    owner_id: int
) -> models.Room:
    # 创建新房间
    db_room = models.Room(
        name=room.name,
        owner_id=owner_id,
        is_active=True
    )
    db.add(db_room)
    await db.commit()
    await db.refresh(db_room)
    return db_room

async def get_room(
    db: AsyncSession, 
    room_id: int
) -> Optional[models.Room]:
    # 获取房间信息
    query = (
        select(models.Room)
        .options(selectinload(models.Room.owner))
        .where(models.Room.id == room_id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_rooms_by_filter(
    db: AsyncSession,
    name: Optional[str] = None,
    owner_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.Room]:
    """
    按条件筛选房间列表。所有参数均为可选，均为空时等价于无条件分页查询。
    :param db: 数据库会话
    :param name: 房间名（模糊匹配）
    :param owner_id: 房主ID
    :param is_active: 是否活跃
    :param skip: 跳过条数
    :param limit: 返回条数
    :return: 房间列表
    """
    query = select(models.Room)
    if name:
        query = query.where(models.Room.name.ilike(f"%{name}%"))
    if owner_id is not None:
        query = query.where(models.Room.owner_id == owner_id)
    if is_active is not None:
        query = query.where(models.Room.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_room_details(
    db: AsyncSession, 
    room_id: int
) -> Optional[models.Room]:
    # 获取房间及其成员信息
    query = (
        select(models.Room)
        .options(
            selectinload(models.Room.owner),
            selectinload(models.Room.members),
            selectinload(models.Room.messages)
        )
        .where(models.Room.id == room_id)
    )
    result = await db.execute(query)
    return result.unique().scalar_one_or_none()

async def add_room_member(
    db: AsyncSession, 
    room_id: int, 
    user_id: int
) -> bool:
    # 添加房间成员
    room = await get_room(db, room_id)
    user = await db.get(models.User, user_id)
    
    if room and user:
        room.members.append(user)
        await db.commit()
        return True
    return False

async def remove_room_member(
    db: AsyncSession, 
    room_id: int, 
    user_id: int
) -> bool:
    # 移除房间成员
    room = await get_room_details(db, room_id)
    if room:
        room.members = [m for m in room.members if m.id != user_id]
        await db.commit()
        return True
    return False

async def update_room(
    db: AsyncSession, 
    room_id: int, 
    update_data: dict
) -> Optional[models.Room]:
    # 更新房间信息
    room = await get_room(db, room_id)
    if room:
        for key, value in update_data.items():
            setattr(room, key, value)
        await db.commit()
        await db.refresh(room)
    return room

async def delete_room(
    db: AsyncSession, 
    room_id: int
) -> bool:
    # 删除房间
    room = await get_room(db, room_id)
    if room:
        await db.delete(room)
        await db.commit()
        return True
    return False
