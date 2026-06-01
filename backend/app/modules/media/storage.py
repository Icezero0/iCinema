import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError
from app.modules.media.constants import MediaAssetType

settings = get_settings()


@dataclass
class SavedMediaFile:
    storage_key: str
    mime_type: str
    file_size: int
    sha256: str
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None


@dataclass
class PreparedUploadFile:
    content: bytes
    mime_type: str
    file_size: int
    sha256: str
    ext: str
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None


class MediaStorageService:
    AVATAR_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
    AVATAR_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

    IMAGE_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    IMAGE_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    STICKER_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    STICKER_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    FEEDBACK_IMAGE_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
    FEEDBACK_IMAGE_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

    def _get_base_dir(self, asset_type: str) -> Path:
        if asset_type == MediaAssetType.AVATAR:
            return settings.avatar_dir_path
        if asset_type == MediaAssetType.IMAGE:
            return settings.image_dir_path
        if asset_type == MediaAssetType.STICKER:
            return settings.sticker_dir_path
        if asset_type == MediaAssetType.VIDEO:
            return settings.video_dir_path
        if asset_type == MediaAssetType.FEEDBACK_IMAGE:
            return settings.feedback_image_dir_path
        raise BadRequestError(
            "Unsupported media asset type",
            reason=ErrorReason.UNSUPPORTED_MEDIA_ASSET_TYPE,
            details={"asset_type": asset_type},
        )

    def _get_allowed_types(self, asset_type: str) -> set[str]:
        if asset_type == MediaAssetType.AVATAR:
            return self.AVATAR_ALLOWED_TYPES
        if asset_type == MediaAssetType.IMAGE:
            return self.IMAGE_ALLOWED_TYPES
        if asset_type == MediaAssetType.STICKER:
            return self.STICKER_ALLOWED_TYPES
        if asset_type == MediaAssetType.FEEDBACK_IMAGE:
            return self.FEEDBACK_IMAGE_ALLOWED_TYPES
        raise BadRequestError(
            "Unsupported upload media type",
            reason=ErrorReason.UNSUPPORTED_UPLOAD_MEDIA_TYPE,
            details={"asset_type": asset_type},
        )

    def _get_allowed_exts(self, asset_type: str) -> set[str]:
        if asset_type == MediaAssetType.AVATAR:
            return self.AVATAR_ALLOWED_EXTS
        if asset_type == MediaAssetType.IMAGE:
            return self.IMAGE_ALLOWED_EXTS
        if asset_type == MediaAssetType.STICKER:
            return self.STICKER_ALLOWED_EXTS
        if asset_type == MediaAssetType.FEEDBACK_IMAGE:
            return self.FEEDBACK_IMAGE_ALLOWED_EXTS
        raise BadRequestError(
            "Unsupported upload media type",
            reason=ErrorReason.UNSUPPORTED_UPLOAD_MEDIA_TYPE,
            details={"asset_type": asset_type},
        )

    async def prepare_upload(
        self,
        *,
        file: UploadFile,
        asset_type: str,
    ) -> PreparedUploadFile:
        content_type = (file.content_type or "").lower()
        if content_type not in self._get_allowed_types(asset_type):
            raise BadRequestError(
                "Unsupported media file type",
                reason=ErrorReason.UNSUPPORTED_MEDIA_FILE_TYPE,
                details={
                    "asset_type": asset_type,
                    "content_type": content_type or None,
                },
            )

        ext = Path(file.filename or "").suffix.lower()
        if ext not in self._get_allowed_exts(asset_type):
            if content_type == "image/jpeg":
                ext = ".jpg"
            elif content_type == "image/png":
                ext = ".png"
            elif content_type == "image/webp":
                ext = ".webp"
            elif content_type == "image/gif":
                ext = ".gif"
            else:
                raise BadRequestError(
                    "Unsupported media file extension",
                    reason=ErrorReason.UNSUPPORTED_MEDIA_FILE_EXTENSION,
                    details={
                        "asset_type": asset_type,
                        "extension": ext or None,
                        "content_type": content_type or None,
                    },
                )

        content = await file.read()
        if not content:
            raise BadRequestError(
                "Media file cannot be empty",
                reason=ErrorReason.EMPTY_MEDIA_FILE,
                details={"asset_type": asset_type},
            )

        return PreparedUploadFile(
            content=content,
            mime_type=content_type,
            file_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            ext=ext,
            width=None,
            height=None,
            duration_seconds=None,
        )

    def save_prepared_upload(
        self,
        *,
        prepared: PreparedUploadFile,
        asset_type: str,
    ) -> SavedMediaFile:
        base_dir = self._get_base_dir(asset_type)
        base_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4().hex}{prepared.ext}"
        target = base_dir / filename
        target.write_bytes(prepared.content)

        return SavedMediaFile(
            storage_key=filename,
            mime_type=prepared.mime_type,
            file_size=prepared.file_size,
            sha256=prepared.sha256,
            width=prepared.width,
            height=prepared.height,
            duration_seconds=prepared.duration_seconds,
        )

    def copy_media_file(
        self,
        *,
        source_asset_type: str,
        source_storage_key: str,
        target_asset_type: str,
    ) -> str:
        source = self.get_file_path(
            asset_type=source_asset_type,
            storage_key=source_storage_key,
        )
        if not source.exists():
            raise FileNotFoundError(source)

        target_dir = self._get_base_dir(target_asset_type)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4().hex}{source.suffix.lower()}"
        target = target_dir / filename
        shutil.copyfile(source, target)
        return filename

    def get_file_path(self, *, asset_type: str, storage_key: str) -> Path:
        if "/" in storage_key or "\\" in storage_key or ".." in storage_key:
            raise BadRequestError(
                "Invalid media storage key",
                reason=ErrorReason.INVALID_MEDIA_STORAGE_KEY,
                details={"asset_type": asset_type},
            )

        return self._get_base_dir(asset_type) / storage_key
    
    def delete_file(
        self,
        *,
        asset_type: str,
        storage_key: str,
    ) -> None:
        path = self.get_file_path(asset_type=asset_type, storage_key=storage_key)
        if path.exists():
            path.unlink()
