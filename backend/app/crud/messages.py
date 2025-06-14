# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from sqlalchemy.orm import joinedload
# from .. import models, schemas
# from typing import Optional, List
# from datetime import datetime

# async def create_message(
#     db: AsyncSession, 
#     message: schemas.MessageCreate, 
#     user_id: int
# ) -> models.Message:
#     # 创建新消息
#     db_message = models.Message(
#         content=message.content,
#         user_id=user_id,
#         room_id=message.room_id
#     )
#     db.add(db_message)
#     await db.commit()
#     await db.refresh(db_message)
#     return db_message

# async def get_message(
#     db: AsyncSession, 
#     message_id: int
# ) -> Optional[models.Message]:
#     # 获取消息
#     query = select(models.Message).where(models.Message.id == message_id)
#     result = await db.execute(query)
#     return result.scalar_one_or_none()

# async def get_room_messages(
#     db: AsyncSession, 
#     room_id: int,
#     skip: int = 0, 
#     limit: int = 50
# ) -> List[models.Message]:
#     # 获取房间的消息列表
#     query = (
#         select(models.Message)
#         .where(models.Message.room_id == room_id)
#         .order_by(models.Message.created_at.desc())
#         .offset(skip)
#         .limit(limit)
#     )
#     result = await db.execute(query)
#     return result.scalars().all()

# async def get_message_with_user(
#     db: AsyncSession, 
#     message_id: int
# ) -> Optional[models.Message]:
#     # 获取消息及其用户信息
#     query = (
#         select(models.Message)
#         .options(joinedload(models.Message.user))
#         .where(models.Message.id == message_id)
#     )
#     result = await db.execute(query)
#     return result.unique().scalar_one_or_none()

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
#         message.content = content
#         await db.commit()
#         await db.refresh(message)
#     return message
