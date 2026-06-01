from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import normalize_optional_non_empty_str, normalize_required_str
from app.modules.feedback.constants import FeedbackPage, FeedbackStatus, FeedbackType
from app.modules.users.schemas import UserBriefResponse


class FeedbackUpdateRequest(BaseModel):
    status: FeedbackStatus | None = None
    admin_note: str | None = None

    @field_validator("admin_note", mode="before")
    @classmethod
    def validate_admin_note(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Admin note")


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    handled_by_id: int | None
    feedback_type: FeedbackType
    page: FeedbackPage
    title: str
    description: str
    status: FeedbackStatus
    admin_note: str | None
    handled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    creator: UserBriefResponse | None = None
    handled_by: UserBriefResponse | None = None
    screenshot_asset_ids: list[int] = Field(default_factory=list)
    screenshot_urls: list[str] = Field(default_factory=list)


class FeedbackListResponse(BaseModel):
    items: list[FeedbackResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int


def normalize_feedback_title(value: str) -> str:
    return normalize_required_str(value, field_name="Title")


def normalize_feedback_description(value: str) -> str:
    return normalize_required_str(value, field_name="Description")
