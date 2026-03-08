from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field
from app.core.config import get_settings

settings = get_settings()


class UserCreate(BaseModel):
    email: EmailStr
    username: str | None = None
    password: str


class UserPatch(BaseModel):
    username: str | None = None
    password: str | None = None
    auto_accept: bool | None = None


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
        print(settings.avatar_public_prefix)
        return f"{settings.avatar_public_prefix}/{self.avatar_key}"


class UserMeResponse(UserResponse):
    pass


class AvatarUploadResponse(BaseModel):
    avatar_url: str | None