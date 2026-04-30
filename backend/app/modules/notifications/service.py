from datetime import datetime, timezone
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.notifications.constants import NotificationType
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import NotificationCreate
from app.modules.users.models import User


class NotificationService:
    def __init__(self) -> None:
        self.repo = NotificationRepository()

    async def find_notification_by_id(
        self,
        db: AsyncSession,
        notification_id: int,
    ) -> Notification | None:
        return await self.repo.find_notification_by_id(db, notification_id)

    async def get_notification_by_id(
        self,
        db: AsyncSession,
        *,
        notification_id: int,
        user: User,
    ) -> Notification:
        notification = await self.find_notification_by_id(db, notification_id)
        if notification is None:
            raise NotFoundError(
                "Notification not found",
                reason=ErrorReason.NOTIFICATION_NOT_FOUND,
                details={"notification_id": notification_id},
            )

        if notification.recipient_user_id != user.id:
            raise ForbiddenError(
                "You do not have permission to perform this action",
                reason=ErrorReason.NOTIFICATION_PERMISSION_DENIED,
                details={"notification_id": notification_id},
            )

        return notification

    async def get_notifications(
        self,
        db: AsyncSession,
        *,
        user: User,
        page: int,
        page_size: int,
        is_read: bool | None = None,
        notification_type: NotificationType | None = None,
    ) -> dict[str, object]:
        items, total = await self.repo.get_notifications(
            db,
            recipient_user_id=user.id,
            page=page,
            page_size=page_size,
            is_read=is_read,
            notification_type=notification_type.value if notification_type else None,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_unread_count(
        self,
        db: AsyncSession,
        *,
        user: User,
    ) -> int:
        return await self.repo.count_unread_notifications(
            db,
            recipient_user_id=user.id,
        )

    async def create_notification_in_tx(
        self,
        db: AsyncSession,
        *,
        payload: NotificationCreate,
    ) -> None:
        # This helper participates in the caller's transaction and does not commit.
        await self.repo.create_notification(
            db,
            recipient_user_id=payload.recipient_user_id,
            actor_user_id=payload.actor_user_id,
            notification_type=payload.notification_type.value,
            related_type=payload.related_type.value if payload.related_type else None,
            related_id=payload.related_id,
        )

    async def create_notification(
        self,
        db: AsyncSession,
        *,
        payload: NotificationCreate,
    ) -> Notification:
        notification = await self.repo.create_notification(
            db,
            recipient_user_id=payload.recipient_user_id,
            actor_user_id=payload.actor_user_id,
            notification_type=payload.notification_type.value,
            related_type=payload.related_type.value if payload.related_type else None,
            related_id=payload.related_id,
        )
        await db.commit()
        return notification

    async def mark_as_read(
        self,
        db: AsyncSession,
        *,
        notification_id: int,
        user: User,
    ) -> Notification:
        notification = await self.get_notification_by_id(
            db,
            notification_id=notification_id,
            user=user,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            notification = await self.repo.save_notification(db, notification)
            await db.commit()

        return notification

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        *,
        user: User,
    ) -> None:
        await self.repo.mark_all_as_read(
            db,
            recipient_user_id=user.id,
        )
        await db.commit()
