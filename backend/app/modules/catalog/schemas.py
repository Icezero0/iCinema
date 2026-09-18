from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ContentType = Literal["tv", "movie", "ova", "oad", "ona", "special"]
ContentStatus = Literal["draft", "published", "withdrawn"]


class ContentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    aliases: str = Field(default="", max_length=1000)
    category: str = Field(default="japanese_animation", min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_]*$")
    region: str = Field(default="", max_length=16)
    content_type: ContentType = "tv"
    year: int | None = Field(default=None, ge=1900, le=2100)
    description: str = Field(default="", max_length=10000)


class ContentUpdate(ContentInput):
    version: int = Field(ge=1)
    status: ContentStatus
    disabled: bool
    disabled_reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_disabled_reason(self):
        if self.disabled and not self.disabled_reason:
            raise ValueError("禁用资源时请填写原因")
        if not self.disabled:
            self.disabled_reason = ""
        return self


class ContentResponse(ContentInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ContentStatus
    disabled: bool
    disabled_reason: str
    version: int
    created_at: datetime
    updated_at: datetime


class ContentListResponse(BaseModel):
    items: list[ContentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    changes: dict
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
