from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MediaAssetUploadResponse(BaseModel):
    id: int
    asset_type: str
    url: str
    mime_type: str
    file_size: int
    status: str


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_type: str
    storage_key: str
    mime_type: str
    file_size: int
    width: int | None
    height: int | None
    duration_seconds: int | None
    sha256: str | None
    uploaded_by_user_id: int | None
    status: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    url: str