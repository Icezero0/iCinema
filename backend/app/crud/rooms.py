from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, insert, select
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
    limit: int = 20
) -> tuple[List[models.Room], int]:
    """
    按条件筛选房间列表。所有参数均为可选，均为空时等价于无条件分页查询。
    :param db: 数据库会话
    :param name: 房间名（模糊匹配）
    :param owner_id: 房主ID
    :param is_active: 是否活跃
    :param skip: 跳过条数
    :param limit: 返回条数
    :return: 元组 (房间列表, 总数)
    """
    base_query = select(models.Room)
    if name:
        base_query = base_query.where(models.Room.name.ilike(f"%{name}%"))
    if owner_id is not None:
        base_query = base_query.where(models.Room.owner_id == owner_id)
    if is_active is not None:
        base_query = base_query.where(models.Room.is_active == is_active)
    
    # 计算总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 获取分页数据
    query = base_query.offset(skip).limit(limit)
    result = await db.execute(query)
    db_rooms = list(result.scalars().all())

    # 返回房间列表和总数，而不是转换为 schema
    return db_rooms, total

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

async def get_room_member_ids(
    db: AsyncSession, 
    room_id: int
) -> List[int]:
    # 获取房间成员信息
    result = await db.execute(
        select(models.room_members.c.user_id)
        .where(models.room_members.c.room_id == room_id)
    )
    member_ids = result.scalars().all()
    return list(member_ids)
    

async def add_room_member(
    db: AsyncSession, 
    room_id: int, 
    user_id: int
) -> bool:
    # 添加房间成员
    stmt = insert(models.room_members).values(room_id=room_id, user_id=user_id, user_type=models.UserType.MEMBER)
    await db.execute(stmt)
    await db.commit()
    return True

async def remove_room_member(
    db: AsyncSession, 
    room_id: int, 
    user_id: int
) -> bool:
    # 移除房间成员
    stmt = (
        models.room_members.delete()
        .where(
            models.room_members.c.room_id == room_id,
            models.room_members.c.user_id == user_id
        )
    )
    await db.execute(stmt)
    await db.commit()
    return True

async def update_room(
    db: AsyncSession, 
    room_id: int, 
    update_data: dict
) -> Optional[models.Room]:
    # 更新房间信息
    db_room = await get_room(db, room_id)
    if db_room:
        for key, value in update_data.items():
            setattr(db_room, key, value)
        await db.commit()
        await db.refresh(db_room)
    return db_room

async def delete_room(
    db: AsyncSession, 
    room_id: int
) -> bool:
    # 删除房间
    db_room = await get_room(db, room_id)
    if db_room:
        await db.delete(db_room)
        await db.commit()
        return True
    return False

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

async def is_room_member(
    db: AsyncSession, 
    room_id: int, 
    user_id: int
) -> bool:
    """
    检查用户是否是房间的成员
    
    参数:
    - db: 数据库会话
    - room_id: 房间ID
    - user_id: 用户ID
    
    返回:
    - 布尔值，表示用户是否是房间成员
    """
    # 直接查询关联表中是否存在对应记录
    query = select(1).select_from(models.room_members).where(
        and_(
            models.room_members.c.room_id == room_id,
            models.room_members.c.user_id == user_id
        )
    )
    
    result = await db.execute(query)
    return result.first() is not None

async def get_joined_rooms(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    include_details: bool = False
) -> tuple[List[models.Room], int]:
    """
    获取用户已加入的房间列表
    
    参数:
    - db: 数据库会话
    - user_id: 用户ID
    - skip: 跳过条数，用于分页
    - limit: 返回条数，用于分页
    - include_details: 是否包含房间详细信息（如成员列表等）
    
    返回:
    - 元组 (房间列表, 总数)
    """
    # 构建查询
    base_query = (
        select(models.Room)
        .join(models.room_members, models.Room.id == models.room_members.c.room_id)
        .where(models.room_members.c.user_id == user_id)
    )
    
    # 计算总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 如果需要包含详细信息，添加预加载选项
    if include_details:
        base_query = base_query.options(
            selectinload(models.Room.owner),
            selectinload(models.Room.members)
        )
    
    # 添加分页
    query = base_query.offset(skip).limit(limit).order_by(models.Room.name)
    
    # 执行查询
    result = await db.execute(query)
    db_rooms = list(result.scalars().all())
    
    return db_rooms, total

async def get_owned_rooms(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    include_details: bool = False
) -> tuple[List[models.Room], int]:
    """
    获取用户拥有的房间列表
    
    参数:
    - db: 数据库会话
    - user_id: 用户ID
    - skip: 跳过条数，用于分页
    - limit: 返回条数，用于分页
    - include_details: 是否包含房间详细信息（如成员列表等）
    
    返回:
    - 元组 (房间列表, 总数)
    """
    # 构建查询，查找用户作为房主的房间
    base_query = select(models.Room).where(models.Room.owner_id == user_id)
    
    # 计算总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 如果需要包含详细信息，添加预加载选项
    if include_details:
        base_query = base_query.options(
            selectinload(models.Room.owner),
            selectinload(models.Room.members)
        )
    
    # 添加分页
    query = base_query.offset(skip).limit(limit).order_by(models.Room.name)
    
    # 执行查询
    result = await db.execute(query)
    db_rooms = list(result.scalars().all())
    
    return db_rooms, total

async def get_user_rooms(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    include_owned: bool = True,
    include_joined: bool = True,
    include_details: bool = False
) -> tuple[List[models.Room], int]:
    """
    获取用户相关的所有房间（包括拥有的和加入的）
    
    参数:
    - db: 数据库会话
    - user_id: 用户ID
    - skip: 跳过条数，用于分页
    - limit: 返回条数，用于分页
    - include_owned: 是否包含用户拥有的房间
    - include_joined: 是否包含用户加入的房间
    - include_details: 是否包含房间详细信息
    
    返回:
    - 元组 (房间列表, 总数)
    """
    # 构建基础查询
    conditions = []
    
    # 添加查询条件
    if include_owned:
        conditions.append(models.Room.owner_id == user_id)
    
    if include_joined:
        # 用户作为成员加入的房间
        member_condition = models.Room.id.in_(
            select(models.room_members.c.room_id)
            .where(models.room_members.c.user_id == user_id)
        )
        conditions.append(member_condition)
    
    # 如果没有任何条件，直接返回空列表
    if not conditions:
        return [], 0
    
    # 组合条件 (OR)
    base_query = select(models.Room).where(
        func.or_(*conditions)
    )
    
    # 计算总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 如果需要包含详细信息，添加预加载选项
    if include_details:
        base_query = base_query.options(
            selectinload(models.Room.owner),
            selectinload(models.Room.members)
        )
    
    # 添加分页和排序
    query = (
        base_query
        .offset(skip)
        .limit(limit)
        .order_by(models.Room.name)
    )
    
    # 执行查询
    result = await db.execute(query)
    db_rooms = list(result.scalars().all())
    
    return db_rooms, total
