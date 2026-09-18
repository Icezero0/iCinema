"""Admin graph editing. The parent version serializes all changes to a work."""
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator, model_validator

from .schemas import ContentResponse


class StateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    disabled: bool = False
    disabled_reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_disabled(self):
        if self.disabled and not self.disabled_reason:
            raise ValueError("A disable reason is required")
        if not self.disabled:
            self.disabled_reason = ""
        return self


class EpisodeInput(StateInput):
    title: str = Field(min_length=1, max_length=255)
    kind: Literal["episode", "special", "movie"] = "episode"
    number: float = Field(default=1, ge=0, le=99999, allow_inf_nan=False)
    sort_order: float = Field(default=0, ge=0, le=999999, allow_inf_nan=False)


class LineInput(StateInput):
    name: str = Field(min_length=1, max_length=100)
    source_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    line_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    sort_order: int = Field(default=0, ge=0, le=999999)


class PlaybackInput(StateInput):
    episode_id: int = Field(ge=1)
    line_id: int = Field(ge=1)
    source_label: str = Field(default="", max_length=255)
    media_type: Literal["hls", "direct", "page"] = "hls"
    url: str = Field(min_length=1, max_length=4096)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        # Preserve signed URLs exactly; validate without rewriting/decoding them.
        TypeAdapter(HttpUrl).validate_python(value)
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError("An HTTP(S) URL without credentials is required")
        if "\\" in value or any(ord(char) < 33 or ord(char) == 127 for char in value):
            raise ValueError("Invalid URL characters")
        return value


class EpisodeMutation(EpisodeInput):
    version: int = Field(ge=1)


class LineMutation(LineInput):
    version: int = Field(ge=1)


class PlaybackMutation(PlaybackInput):
    version: int = Field(ge=1)


class EpisodeResponse(EpisodeInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content_id: int
    available_line_count: int = 0


class LineResponse(LineInput):
    model_config = ConfigDict(from_attributes=True)
    display_name: str = ""
    id: int
    content_id: int


class PlaybackResponse(PlaybackInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content_id: int


class GraphResponse(BaseModel):
    content: ContentResponse
    episodes: list[EpisodeResponse]
    lines: list[LineResponse]
    playbacks: list[PlaybackResponse]


class PreviewResponse(BaseModel):
    url: str
    media_type: Literal["hls", "direct"]
