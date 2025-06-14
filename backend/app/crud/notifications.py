from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from .. import models
from typing import Optional

async def create_notification(
    db: AsyncSession, 
    recipient_id: int,
    content: str,
    sender_id: Optional[int] = None,  # 添加 sender_id 作为可选参数
    status: str = "unread"
) -> models.Notification:
    notification = models.Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,  # 使用传入的 sender_id 值
        content=content,
        status=status
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification

async def get_notification_list_by_userid(
    db: AsyncSession, 
    user_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
) -> schemas.NotificationList:
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
    notifications = [
        schemas.NotificationResponse.model_validate(notification) for notification in db_notifications
    ]
    
    # 返回符合 NotificationList 模式的数据
    return schemas.NotificationListResponse(
        items=list(notifications),
        total=total
    )