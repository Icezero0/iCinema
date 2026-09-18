from datetime import datetime, date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .provider_client import validate_endpoint


class ProviderInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    abbreviation: str = Field(default="", max_length=32)
    endpoint: str = Field(min_length=1, max_length=255)
    enabled: bool
    category: str = Field(min_length=1, max_length=32)
    upstream_category: int = Field(ge=1, le=999999)
    play_from: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    version: int = Field(ge=1)

    @field_validator("endpoint")
    @classmethod
    def valid_endpoint(cls, value):
        from app.core.exceptions import BadRequestError
        try:
            validate_endpoint(value)
        except BadRequestError as exc:
            raise ValueError(exc.message) from exc
        return value


class ProviderCreate(ProviderInput):
    code: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    version: int = Field(default=1, ge=1, le=1)


class ProviderResponse(ProviderInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str


class PreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_page: int = Field(default=1, ge=1, le=10000)
    page_count: int = Field(default=1, ge=1, le=3)
    max_items: int = Field(default=20, ge=1, le=60)


class DiscoveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(default="", max_length=255)
    category: str = Field(min_length=1, max_length=32)
    updated_from: date | None = None
    updated_to: date | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.updated_from and self.updated_to and self.updated_from > self.updated_to:
            raise ValueError("Invalid date range")
        return self


class SelectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keys: list[str] = Field(min_length=1, max_length=5000)


class CandidateSource(BaseModel):
    provider_id: int
    provider_name: str
    upstream_id: int
    title: str
    updated: str = ""
    episode_count: int = 0
    warnings: list[str] = []


class ImportItem(BaseModel):
    upstream_id: int
    title: str
    status: str = "pending"
    reason: str = ""
    content_id: int | None = None
    warnings: list[str] = []
    entries: int = 0
    key: str = ""
    sources: list[CandidateSource] = []
    line_count: int = 0
    episode_count: int = 0
    new_episodes: int = 0
    blocked: bool = False
    match: str = ""


class ImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider_id: int
    provider_version: int
    status: str
    start_page: int
    page_count: int
    items: list[ImportItem]
    warnings: list[str]
    query: dict = {}
    created_at: datetime
    updated_at: datetime


class ImportListResponse(BaseModel):
    items: list[ImportResponse]
    total: int
    page: int
    total_pages: int
