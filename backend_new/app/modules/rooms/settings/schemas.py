from pydantic import BaseModel, ConfigDict

from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomMediaSourceType,
    RoomSyncPolicy,
)


class RoomSettingsPatch(BaseModel):
    selected_room_video_source_type: RoomMediaSourceType | None = None
    sync_policy: RoomSyncPolicy | None = None
    active_sync_permission: RoomActiveSyncPermission | None = None


class RoomSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    selected_room_video_source_type: RoomMediaSourceType
    sync_policy: RoomSyncPolicy
    active_sync_permission: RoomActiveSyncPermission