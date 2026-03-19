from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.notifications.models import Notification


class NotificationRepository:
    async def create_notification(
        self,
        db: AsyncSession,
        *,
        recipient_user_id: int,
        actor_user_id: int | None,
        notification_type: str,
        related_type: str | None,
        related_id: int | None,
    ) -> Notification:
        notification = Notification(
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            notification_type=notification_type,
            related_type=related_type,
            related_id=related_id,
        )
        db.add(notification)
        await db.flush()
        await db.refresh(notification)
        return notification

    async def find_notification_by_id(
        self,
        db: AsyncSession,
        notification_id: int,
    ) -> Notification | None:
        result = await db.execute(
            select(Notification)
            .where(Notification.id == notification_id)
            .options(selectinload(Notification.actor))
        )
        return result.scalar_one_or_none()

    async def get_notifications(
        self,
        db: AsyncSession,
        *,
        recipient_user_id: int,
        page: int,
        page_size: int,
        is_read: bool | None = None,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        stmt = (
            select(Notification)
            .where(Notification.recipient_user_id == recipient_user_id)
            .options(selectinload(Notification.actor))
        )
        count_stmt = select(func.count()).select_from(Notification).where(
            Notification.recipient_user_id == recipient_user_id
        )

        if is_read is not None:
            stmt = stmt.where(Notification.is_read.is_(is_read))
            count_stmt = count_stmt.where(Notification.is_read.is_(is_read))

        if notification_type is not None:
            stmt = stmt.where(Notification.notification_type == notification_type)
            count_stmt = count_stmt.where(
                Notification.notification_type == notification_type
            )

        stmt = (
            stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items = list(result.scalars().all())

        total = await db.scalar(count_stmt)
        return items, int(total or 0)

    async def count_unread_notifications(
        self,
        db: AsyncSession,
        *,
        recipient_user_id: int,
    ) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.recipient_user_id == recipient_user_id,
            Notification.is_read.is_(False),
        )
        total = await db.scalar(stmt)
        return int(total or 0)

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        *,
        recipient_user_id: int,
    ) -> None:
        await db.execute(
            update(Notification)
            .where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=func.now(),
            )
        )
        await db.flush()

    async def save_notification(
        self,
        db: AsyncSession,
        notification: Notification,
    ) -> Notification:
        db.add(notification)
        await db.flush()
        return notification