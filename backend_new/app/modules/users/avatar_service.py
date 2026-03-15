from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

settings = get_settings()


class AvatarService:
    ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
    ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

    async def save_avatar(self, file: UploadFile, user_id: int) -> str:
        if file.content_type not in self.ALLOWED_TYPES:
            raise BadRequestError("Unsupported avatar file type")

        ext = Path(file.filename or "").suffix.lower()
        if ext not in self.ALLOWED_EXTS:
            ext = ".png"

        avatar_dir = settings.avatar_dir_path
        avatar_dir.mkdir(parents=True, exist_ok=True)

        filename = f"user_{user_id}_{uuid4().hex}{ext}"
        target = avatar_dir / filename

        content = await file.read()
        if not content:
            raise BadRequestError("Avatar file cannot be empty")

        target.write_bytes(content)
        return filename