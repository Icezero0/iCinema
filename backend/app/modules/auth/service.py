from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.users.repository import UserRepository


class AuthService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()

    def _build_token_response(self, user_id: int) -> dict:
        return {
            "access_token": create_access_token(str(user_id)),
            "refresh_token": create_refresh_token(str(user_id)),
            "token_type": "bearer",
        }

    async def login(self, db: AsyncSession, *, email: str, password: str) -> dict:
        user = await self.user_repo.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError(
                "Invalid email or password",
                reason=ErrorReason.INVALID_CREDENTIALS,
            )

        return self._build_token_response(user.id)

    async def refresh_tokens(self, db: AsyncSession, *, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except Exception as e:  # noqa: BLE001
            raise UnauthorizedError(
                "Invalid refresh token",
                reason=ErrorReason.INVALID_REFRESH_TOKEN,
            ) from e

        if payload.get("type") != "refresh":
            raise UnauthorizedError(
                "Invalid token type",
                reason=ErrorReason.INVALID_TOKEN_TYPE,
                details={"expected": "refresh", "actual": payload.get("type")},
            )

        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError(
                "Invalid token payload",
                reason=ErrorReason.INVALID_TOKEN_PAYLOAD,
                details={"field": "sub"},
            )

        try:
            user_id = int(sub)
        except (TypeError, ValueError) as e:
            raise UnauthorizedError(
                "Invalid token payload",
                reason=ErrorReason.INVALID_TOKEN_PAYLOAD,
                details={"field": "sub", "constraint": "integer"},
            ) from e

        user = await self.user_repo.get_by_id(db, user_id)
        if not user:
            raise UnauthorizedError("User not found", reason=ErrorReason.USER_NOT_FOUND)

        return self._build_token_response(user.id)
