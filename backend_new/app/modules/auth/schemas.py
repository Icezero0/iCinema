from pydantic import BaseModel, EmailStr, field_validator

from app.core.validators import normalize_email, normalize_required_str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return normalize_required_str(value, field_name="Password")


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    @field_validator("refresh_token", mode="before")
    @classmethod
    def validate_refresh_token(cls, value: str) -> str:
        return normalize_required_str(value, field_name="Refresh token")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"