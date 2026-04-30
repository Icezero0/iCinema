from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.core.validators import normalize_email
from app.modules.media.service import MediaService
from app.modules.rooms.constants import RoomRole
from app.modules.rooms.room.repository import RoomRepository
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserPatch


class UserService:
    def __init__(self) -> None:
        self.repo = UserRepository()
        self.media_service = MediaService()
        self.room_repo = RoomRepository()

    async def hydrate_user_avatar_key(self, db: AsyncSession, user: User) -> User:
        avatar_key = await self.media_service.get_user_avatar_storage_key(db, user.id)
        user.avatar_key = avatar_key
        return user

    async def hydrate_users_avatar_key(self, db: AsyncSession, users: list[User]) -> list[User]:
        if not users:
            return users

        user_ids = [user.id for user in users]
        avatar_key_map = await self.media_service.get_user_avatar_storage_key_map(db, user_ids)

        for user in users:
            user.avatar_key = avatar_key_map.get(user.id)

        return users

    async def create_user(self, db: AsyncSession, payload: UserCreate) -> User:
        if await self.repo.get_by_email(db, payload.email):
            raise ConflictError(
                "Email already exists",
                reason=ErrorReason.EMAIL_ALREADY_EXISTS,
                details={"field": "email"},
            )

        user = await self.repo.create(
            db,
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        await db.commit()
        return await self.hydrate_user_avatar_key(db, user)

    async def find_user_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        return await self.repo.get_by_id(db, user_id)

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User:
        user = await self.find_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(
                "User not found",
                reason=ErrorReason.USER_NOT_FOUND,
                details={"user_id": user_id},
            )
        return await self.hydrate_user_avatar_key(db, user)

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

        items = await self.hydrate_users_avatar_key(db, items)

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_my_rooms(
        self,
        db: AsyncSession,
        *,
        user: User,
        page: int,
        page_size: int,
        role: RoomRole | None = None,
    ) -> dict:
        items, total = await self.room_repo.get_user_rooms(
            db,
            user_id=user.id,
            page=page,
            page_size=page_size,
            role=role,
        )

        owners = [room.owner for room, _ in items if room.owner is not None]
        await self.hydrate_users_avatar_key(db, owners)

        total_pages = ceil(total / page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_my_owned_rooms(
        self,
        db: AsyncSession,
        *,
        user: User,
        page: int,
        page_size: int,
    ) -> dict:
        return await self.get_my_rooms(
            db,
            user=user,
            page=page,
            page_size=page_size,
            role=RoomRole.OWNER,
        )

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
        return await self.hydrate_user_avatar_key(db, user)

    async def update_avatar(self, db: AsyncSession, user: User, file) -> User:
        await self.media_service.create_avatar_asset_in_tx(
            db,
            file=file,
            user=user,
        )
        user = await self.repo.save(db, user)
        await db.commit()
        return await self.hydrate_user_avatar_key(db, user)
