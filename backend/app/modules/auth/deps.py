from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.error_reasons import ErrorReason
from app.core.exceptions import UnauthorizedError
from app.core.logging import set_log_context
from app.core.security import decode_token
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise UnauthorizedError(
            "Missing authorization token",
            reason=ErrorReason.MISSING_AUTHORIZATION_TOKEN,
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as e:  # noqa: BLE001
        raise UnauthorizedError("Invalid token", reason=ErrorReason.INVALID_TOKEN) from e

    if payload.get("type") != "access":
        raise UnauthorizedError(
            "Invalid token type",
            reason=ErrorReason.INVALID_TOKEN_TYPE,
            details={"expected": "access", "actual": payload.get("type")},
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

    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if not user:
        raise UnauthorizedError("User not found", reason=ErrorReason.USER_NOT_FOUND)

    request.state.user_id = user.id
    set_log_context(user_id=user.id)
    return user
