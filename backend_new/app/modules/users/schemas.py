from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.core.config import get_settings
from app.core.validators import (
    normalize_email,
    normalize_optional_non_empty_str,
    normalize_required_str,
)

settings = get_settings()


class UserCreate(BaseModel):
    email: EmailStr
    username: str | None = None
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Username")

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return normalize_required_str(value, field_name="Password")


class UserPatch(BaseModel):
    username: str | None = None
    password: str | None = None
    auto_accept: bool | None = None

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Username")

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        return normalize_optional_non_empty_str(value, field_name="Password")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str | None
    auto_accept: bool

    avatar_key: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        if not self.avatar_key:
            return None
        return f"{settings.avatar_public_prefix}/{self.avatar_key}"


class UserMeResponse(UserResponse):
    pass


class AvatarUploadResponse(BaseModel):
    avatar_url: str | None