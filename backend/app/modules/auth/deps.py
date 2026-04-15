from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise UnauthorizedError("Missing authorization token")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as e:  # noqa: BLE001
        raise UnauthorizedError("Invalid token") from e

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Invalid token payload")

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as e:
        raise UnauthorizedError("Invalid token payload") from e

    repo = UserRepository()
    user = await repo.get_by_id(db, user_id)
    if not user:
        raise UnauthorizedError("User not found")

    return user