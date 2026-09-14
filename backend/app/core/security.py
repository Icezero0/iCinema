from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "type": "access", "iat": now, "exp": exp, "ver": 0}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, *, token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "type": "refresh", "iat": now, "exp": exp, "ver": token_version}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def require_token_version(payload: dict[str, Any], current_version: int) -> None:
    # Pre-migration JWTs are version zero, and are revoked by the first password change.
    version = payload.get("ver", 0)
    if type(version) is not int or version != current_version:
        raise UnauthorizedError("Session has been revoked", reason="session_revoked")
