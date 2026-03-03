from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
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

        if payload.username and await self.repo.get_by_username(db, payload.username):
            raise ConflictError("Username already exists")

        user = await self.repo.create(
            db,
            email=payload.email.strip().lower(),
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        await db.commit()
        return user

    async def get_user_or_404(self, db: AsyncSession, user_id: int) -> User:
        user = await self.repo.get_by_id(db, user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def patch_me(self, db: AsyncSession, user: User, payload: UserPatch) -> User:
        updates = payload.model_dump(exclude_unset=True)

        if "username" in updates:
            new_username = updates["username"]
            if new_username and new_username != user.username:
                existed = await self.repo.get_by_username(db, new_username)
                if existed and existed.id != user.id:
                    raise ConflictError("Username already exists")
            user.username = new_username

        if "password" in updates and updates["password"]:
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