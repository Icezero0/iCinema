from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from .. import models, schemas
from typing import Optional, List, Tuple
from datetime import datetime

async def create_message(
    db: AsyncSession, 
    message: schemas.MessageCreate, 
    room_id: int,
    user_id: int
) -> models.Message:
    # 创建新消息
    db_message = models.Message(
        content=message.content,
        room_id=room_id,
        user_id=user_id
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message

async def get_message(
    db: AsyncSession, 
    message_id: int
) -> Optional[models.Message]:
    # 获取消息
    query = select(models.Message).where(models.Message.id == message_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_room_messages(
    db: AsyncSession, 
    room_id: int,
    skip: int = 0, 
    limit: int = 20
) -> Tuple[List[models.Message], int]:
    count_query = select(func.count()).select_from(models.Message).where(
        models.Message.room_id == room_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # 获取消息列表，包含用户信息
    query = (
        select(models.Message)
        .where(models.Message.room_id == room_id)
        .offset(skip)
        .limit(limit)
        .order_by(models.Message.created_at.asc())
    )
    result = await db.execute(query)
    messages = list(result.unique().scalars().all())
    
    return messages, total

# async def delete_message(
#     db: AsyncSession, 
#     message_id: int
# ) -> bool:
#     # 删除消息
#     message = await get_message(db, message_id)
#     if message:
#         await db.delete(message)
#         await db.commit()
#         return True
#     return False

# async def update_message(
#     db: AsyncSession, 
#     message_id: int, 
#     content: str
# ) -> Optional[models.Message]:
#     # 更新消息内容
#     message = await get_message(db, message_id)
#     if message:
#         message.content = content  # type: ignore
#         await db.commit()
#         await db.refresh(message)
#     return message
