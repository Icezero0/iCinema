from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MediaAssetUploadResponse(BaseModel):
    id: int
    asset_type: str
    url: str
    mime_type: str
    file_size: int
    status: str


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_type: str
    storage_key: str
    mime_type: str
    file_size: int
    width: int | None
    height: int | None
    duration_seconds: int | None
    sha256: str | None
    uploaded_by_user_id: int | None
    status: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    url: str


class StickerResponse(BaseModel):
    id: int
    asset_type: str
    mime_type: str
    file_size: int
    width: int | None
    height: int | None
    status: str
    sort_order: int
    url: str
    created_at: datetime
    updated_at: datetime

class StickerLibraryResponse(BaseModel):
    items: list[StickerResponse] = Field(default_factory=list)
    total: int
    all: bool
    page: int | None = None
    page_size: int | None = None
    total_pages: int | None = None


class StickerLibraryUpdateRequest(BaseModel):
    sticker_ids: list[int]

    @field_validator("sticker_ids")
    @classmethod
    def validate_sticker_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value):
            raise ValueError("sticker_ids must be positive integers")
        if len(set(value)) != len(value):
            raise ValueError("sticker_ids cannot contain duplicates")
        return value


class EmojiAssetResponse(BaseModel):
    type: int
    name: str
    path: str
    url: str


class EmojiResponse(BaseModel):
    provider: str
    id: str
    describe: str | None = None
    assets: list[EmojiAssetResponse]


class EmojiListResponse(BaseModel):
    items: list[EmojiResponse] = Field(default_factory=list)