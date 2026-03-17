from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.exceptions import BadRequestError
from app.core.validators import normalize_optional_non_empty_str, normalize_required_str
from app.modules.notifications.constants import (
    NotificationRelatedType,
    NotificationType,
)
from app.modules.users.schemas import UserBriefResponse


class NotificationCreate(BaseModel):
    recipient_id: int
    sender_id: int | None = None
    notification_type: NotificationType
    title: str
    content: str | None = None
    related_type: NotificationRelatedType | None = None
    related_id: int | None = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return normalize_required_str(value, field_name="Notification title")

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Notification content")

    @model_validator(mode="after")
    def validate_related_fields(self) -> "NotificationCreate":
        if self.notification_type == NotificationType.SYSTEM:
            if self.related_type is not None or self.related_id is not None:
                raise BadRequestError(
                    "System notification must not have related_type or related_id"
                )
            return self

        if self.notification_type == NotificationType.WORKFLOW:
            if self.related_type is None or self.related_id is None:
                raise BadRequestError(
                    "Workflow notification must have related_type and related_id"
                )
            return self

        raise BadRequestError("Unsupported notification type")


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_id: int
    sender_id: int | None
    notification_type: NotificationType
    title: str
    content: str | None
    is_read: bool
    related_type: NotificationRelatedType | None
    related_id: int | None
    created_at: datetime | None

    sender: UserBriefResponse | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int