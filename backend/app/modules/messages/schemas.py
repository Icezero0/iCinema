from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.schemas import UserResponse


class TextSegmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text"] = "text"
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if value == "":
            raise ValueError("text segment cannot be empty")
        return value


class EmojiSegmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["emoji"] = "emoji"
    id: str = Field(min_length=1, max_length=64)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if value == "":
            raise ValueError("emoji id cannot be empty")
        return value


class ImageSegmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["image"] = "image"
    id: int = Field(gt=0)


class StickerSegmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["sticker"] = "sticker"
    id: int = Field(gt=0)


MessageSegmentIn = Annotated[
    Union[
        TextSegmentIn,
        EmojiSegmentIn,
        ImageSegmentIn,
        StickerSegmentIn,
    ],
    Field(discriminator="type"),
]


class MessageContentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[MessageSegmentIn]

    @field_validator("segments")
    @classmethod
    def validate_segments(cls, value: list[MessageSegmentIn]) -> list[MessageSegmentIn]:
        if not value:
            raise ValueError("segments cannot be empty")
        return value


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: MessageContentIn


# ===== response =====


class TextSegmentOut(BaseModel):
    type: Literal["text"] = "text"
    text: str


class EmojiSegmentOut(BaseModel):
    type: Literal["emoji"] = "emoji"
    id: str


class ImageSegmentOut(BaseModel):
    type: Literal["image"] = "image"
    id: int
    url: str | None = None


class StickerSegmentOut(BaseModel):
    type: Literal["sticker"] = "sticker"
    id: int
    url: str | None = None


MessageSegmentOut = Annotated[
    Union[
        TextSegmentOut,
        EmojiSegmentOut,
        ImageSegmentOut,
        StickerSegmentOut,
    ],
    Field(discriminator="type"),
]


class MessageContentOut(BaseModel):
    segments: list[MessageSegmentOut]


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    sender_user_id: int | None
    sender: UserResponse | None = None
    content: MessageContentOut
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    next_before_id: int | None = None