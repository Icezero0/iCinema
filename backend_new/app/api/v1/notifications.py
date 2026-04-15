from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_realtime_publisher
from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.notifications.constants import NotificationType
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User
from app.realtime.publisher import RealtimePublisher

router = APIRouter(prefix="/notifications", tags=["notifications"])

notification_service = NotificationService()


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_read: bool | None = Query(default=None),
    notification_type: NotificationType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    data = await notification_service.get_notifications(
        db,
        user=current_user,
        page=page,
        page_size=page_size,
        is_read=is_read,
        notification_type=notification_type,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        total_pages=data["total_pages"],
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationUnreadCountResponse:
    unread_count = await notification_service.get_unread_count(
        db,
        user=current_user,
    )
    return NotificationUnreadCountResponse(unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    publisher: RealtimePublisher = Depends(get_realtime_publisher),
) -> NotificationResponse:
    notification = await notification_service.mark_as_read(
        db,
        notification_id=notification_id,
        user=current_user,
    )
    await publisher.publish_notification(user_id=current_user.id)
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    publisher: RealtimePublisher = Depends(get_realtime_publisher),
) -> None:
    await notification_service.mark_all_as_read(
        db,
        user=current_user,
    )
    await publisher.publish_notification(user_id=current_user.id)
