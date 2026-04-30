from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError
from app.modules.notifications.constants import (
    NotificationRelatedType,
    NotificationType,
)
from app.modules.users.schemas import UserBriefResponse


class NotificationCreate(BaseModel):
    recipient_user_id: int
    actor_user_id: int | None = None
    notification_type: NotificationType
    related_type: NotificationRelatedType | None = None
    related_id: int | None = None

    @model_validator(mode="after")
    def validate_related_fields(self) -> "NotificationCreate":
        if (self.related_type is None) != (self.related_id is None):
            raise BadRequestError(
                "related_type and related_id must be provided together",
                reason=ErrorReason.NOTIFICATION_RELATED_FIELDS_INCOMPLETE,
                details={
                    "has_related_type": self.related_type is not None,
                    "has_related_id": self.related_id is not None,
                },
            )
        return self


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_user_id: int
    actor_user_id: int | None
    notification_type: NotificationType
    related_type: NotificationRelatedType | None
    related_id: int | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    actor: UserBriefResponse | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int
