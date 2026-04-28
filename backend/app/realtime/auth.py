from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


async def authenticate_websocket_token(
    db: AsyncSession,
    *,
    token: str,
) -> User:
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

    user = await UserRepository().get_by_id(db, user_id)
    if not user:
        raise UnauthorizedError("User not found")
    return user
