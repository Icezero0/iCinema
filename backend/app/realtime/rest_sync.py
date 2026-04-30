from __future__ import annotations

from app.modules.rooms.constants import RoomSyncPolicy
from app.modules.rooms.settings.service import RoomSettingsService
from app.realtime.constants import AutoPlaybackAction, SessionCloseReason
from app.realtime.manager import RealtimeManager
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_presence import RoomPresenceService
from app.realtime.room_video_runtime import RoomVideoRuntimeService


async def close_room_user_session(
    *,
    db,
    manager: RealtimeManager,
    publisher: RealtimePublisher,
    presence_service: RoomPresenceService,
    video_runtime_service: RoomVideoRuntimeService,
    room_id: int,
    user_id: int,
    reason: SessionCloseReason,
) -> bool:
    connection_id = await presence_service.find_room_user_connection(
        room_id=room_id,
        user_id=user_id,
    )
    if connection_id is None:
        return False

    await publisher.publish_session_closed(
        connection_id=connection_id,
        room_id=room_id,
        reason=reason,
    )

    evicted_connection_id = await presence_service.evict_room_user(
        manager=manager,
        room_id=room_id,
        user_id=user_id,
    )
    if evicted_connection_id is None:
        return False

    presence = await presence_service.get_presence_state(room_id=room_id)
    settings = await RoomSettingsService().find_room_settings_by_room_id(
        db,
        room_id=room_id,
    )
    sync_policy = (
        settings.sync_policy if settings is not None else RoomSyncPolicy.AUTO_SYNC
    )

    session_exit_result = await video_runtime_service.handle_room_session_exit(
        room_id=room_id,
        user_id=user_id,
        sync_policy=sync_policy,
        room_empty=not presence.present_user_ids,
    )

    if not session_exit_result.room_cleared and session_exit_result.user_resource_states is not None:
        await publisher.publish_user_resource_states(
            user_resource_states=session_exit_result.user_resource_states,
        )
        if (
            session_exit_result.auto_action == AutoPlaybackAction.PLAY
            and session_exit_result.auto_playback is not None
        ):
            await publisher.publish_playback_play(
                playback=session_exit_result.auto_playback,
            )

    await publisher.publish_room_user_presence(
        presence=presence,
    )
    return True


async def close_room_sessions(
    *,
    manager: RealtimeManager,
    publisher: RealtimePublisher,
    presence_service: RoomPresenceService,
    video_runtime_service: RoomVideoRuntimeService,
    room_id: int,
    reason: SessionCloseReason,
) -> list[int]:
    active_connections = await presence_service.evict_room_users(
        manager=manager,
        room_id=room_id,
    )
    if not active_connections:
        await video_runtime_service.clear_room_runtime(room_id=room_id)
        return []

    for _, connection_id in active_connections:
        await publisher.publish_session_closed(
            connection_id=connection_id,
            room_id=room_id,
            reason=reason,
        )

    await video_runtime_service.clear_room_runtime(room_id=room_id)
    return [user_id for user_id, _ in active_connections]
