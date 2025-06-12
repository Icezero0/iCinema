from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from .. import models, schemas
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import selectinload


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    # 创建新用户
    db_user = models.User(
        username=user.username,
        email=user.email,
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
        .options(
            selectinload(models.User.rooms_owned),
            selectinload(models.User.rooms_joined)
        )
        .where(models.User.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    # 根据邮箱获取用户信息
    result = await db.execute(
        select(models.User)
        .options(
            selectinload(models.User.rooms_owned),
            selectinload(models.User.rooms_joined)
        )
        .where(models.User.email == email)
    )
    return result.scalar_one_or_none()

async def update_user(
    db: AsyncSession, 
    user_id: int, 
    update_data: dict
) -> Optional[models.User]:
    # 只允许更新的字段白名单
    ALLOWED_FIELDS = {"username", "avatar_path", "hashed_password"}
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

async def get_user_with_rooms(db: AsyncSession, user_id: int) -> Optional[models.User]:
    # 获取用户及其房间信息
    query = (
        select(models.User)
        .options(
            selectinload(models.User.rooms_owned),
            selectinload(models.User.rooms_joined)
        )
        .where(models.User.id == user_id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    # 根据用户名查询用户
    result = await db.execute(
        select(models.User).where(models.User.username == username)
    )
    return result.scalar_one_or_none()