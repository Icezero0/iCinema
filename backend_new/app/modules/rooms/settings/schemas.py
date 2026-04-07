from pydantic import BaseModel, ConfigDict

from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomVideoSourceType,
    RoomSyncPolicy,
)


class RoomSettingsPatch(BaseModel):
    selected_room_video_source_type: RoomVideoSourceType | None = None
    sync_policy: RoomSyncPolicy | None = None
    active_sync_permission: RoomActiveSyncPermission | None = None


class RoomSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: int
    selected_room_video_source_type: RoomVideoSourceType
    sync_policy: RoomSyncPolicy
    active_sync_permission: RoomActiveSyncPermission