from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from .. import models
from typing import Optional

async def create_notification(
    db: AsyncSession, 
    recipient_id: int,
    content: str,
    sender_id: Optional[int] = None,
    status: str = "unread"
) -> models.Notification:
    notification = models.Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        content=content,
        status=status
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification

async def get_notification(
    db: AsyncSession, 
    notification_id: int,
) -> Optional[models.Notification]:
    db_notification = await db.get(models.Notification, notification_id)
    return db_notification


async def get_notification_list_by_userid(
    db: AsyncSession, 
    user_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
) -> tuple[list[models.Notification], int]:
    # 查询未删除的通知总数
    count_query = select(func.count()).select_from(models.Notification).where(
        models.Notification.recipient_id == user_id,
        models.Notification.is_deleted == False
    )
    total_count = await db.execute(count_query)
    total = total_count.scalar_one()
    
    
    # 查询分页后的通知列表
    query = (
        select(models.Notification)
        .where(
            models.Notification.recipient_id == user_id,
            models.Notification.is_deleted == False
        )
        .order_by(models.Notification.created_at.desc())  # 按创建时间降序排序
        .offset(skip)  # 跳过前 skip 条记录
        .limit(limit)  # 限制返回 limit 条记录
    )
    
    result = await db.execute(query)
    db_notifications = result.scalars().all()  # 使用 scalars().all() 获取所有结果

    return (list(db_notifications), total)


async def update_notification(
    db: AsyncSession, 
    notification_id: int,
    is_deleted: Optional[bool] = None,
    status: Optional[str] = None
) -> Optional[models.Notification]:
    db_notification = await db.get(models.Notification, notification_id)
    if not db_notification:
        return None
    
    if is_deleted is not None:
        db_notification.is_deleted = is_deleted # type: ignore[reportAttributeAccessIssue]
    if status is not None:
        db_notification.status = status # type: ignore[reportAttributeAccessIssue]
    
    await db.commit()
    await db.refresh(db_notification)
    
    return db_notification

async def delete_notification(
    db: AsyncSession, 
    notification_id: int
) -> bool:
    db_notification = await db.get(models.Notification, notification_id)
    if not db_notification:
        return False
    
    await db.delete(db_notification)
    await db.commit()
    
    return True