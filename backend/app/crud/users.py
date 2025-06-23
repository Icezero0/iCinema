from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from .. import models, schemas
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import selectinload


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    # 创建新用户，邮箱转换为小写以确保大小写不敏感
    db_user = models.User(
        username=user.username,
        email=user.email.lower(),  # 统一转换为小写存储
        hashed_password=user.password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    # 获取用户信息
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    # 根据邮箱获取用户信息，大小写不敏感
    result = await db.execute(
        select(models.User)
        .where(models.User.email == email.lower())  # 转换为小写进行查询
    )
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    # 根据用户名查询用户
    result = await db.execute(
        select(models.User)
        .where(models.User.username == username)
    )
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession, 
    user_id: int, 
    update_data: dict
) -> Optional[models.User]:
    # 只允许更新的字段白名单
    ALLOWED_FIELDS = {"username", "avatar_path", "hashed_password", "auto_accept"}
    query = select(models.User).where(models.User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        for key, value in update_data.items():
            if key in ALLOWED_FIELDS:
                setattr(user, key, value)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            raise e
    return user

async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    email: Optional[str] = None,
    username: Optional[str] = None,
    userid: Optional[int] = None
) -> Tuple[List[models.User], int]:
    query = select(models.User)
    if userid is not None:
        query = query.where(models.User.id == userid)
    if email:
        query = query.where(models.User.email == email.lower())  # 邮箱查询也转换为小写
    if username:
        query = query.where(models.User.username.ilike(f"%{username}%"))
    total_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar()
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    users = list(users)
    total = total if total is not None else 0
    return users, total

# async def delete_user(db: AsyncSession, user_id: int) -> bool:
#     # 删除用户
#     query = select(models.User).where(models.User.id == user_id)
#     result = await db.execute(query)
#     user = result.scalar_one_or_none()
    
#     if user:
#         await db.delete(user)
#         await db.commit()
#         return True
#     return False

