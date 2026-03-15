from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.core.validators import normalize_email
from app.modules.users.avatar_service import AvatarService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserPatch


class UserService:
    def __init__(self) -> None:
        self.repo = UserRepository()
        self.avatar_service = AvatarService()

    async def create_user(self, db: AsyncSession, payload: UserCreate) -> User:
        if await self.repo.get_by_email(db, payload.email):
            raise ConflictError("Email already exists")

        user = await self.repo.create(
            db,
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        await db.commit()
        return user

    async def find_user_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        return await self.repo.get_by_id(db, user_id)

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User:
        user = await self.find_user_by_id(db, user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def find_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        return await self.repo.get_by_email(db, normalize_email(email))

    async def get_users(
        self,
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        username: str | None = None,
        email: str | None = None,
    ) -> dict:
        username = username.strip() if username else None
        email = email.strip().lower() if email else None

        items, total = await self.repo.get_users(
            db,
            page=page,
            page_size=page_size,
            username=username,
            email=email,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def patch_me(self, db: AsyncSession, user: User, payload: UserPatch) -> User:
        updates = payload.model_dump(exclude_unset=True)

        if "username" in updates:
            user.username = updates["username"]

        if "password" in updates:
            user.hashed_password = hash_password(updates["password"])

        if "auto_accept" in updates:
            user.auto_accept = updates["auto_accept"]

        user = await self.repo.save(db, user)
        await db.commit()
        return user

    async def update_avatar(self, db: AsyncSession, user: User, file) -> User:
        key = await self.avatar_service.save_avatar(file=file, user_id=user.id)
        user.avatar_key = key
        user = await self.repo.save(db, user)
        await db.commit()
        return user