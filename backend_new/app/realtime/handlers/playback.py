from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError
from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomMediaSourceType,
    RoomRole,
    RoomSyncPolicy,
)
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.room.service import RoomService
from app.modules.rooms.settings.service import RoomSettingsService
from app.realtime.constants import VideoSourceType, WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_video_runtime import RoomVideoRuntimeService


@dataclass
class PlaybackRuntimePolicy:
    sync_policy: RoomSyncPolicy
    active_sync_permission: RoomActiveSyncPermission


class PlaybackCommandHandler:
    def __init__(self, video_runtime_service: RoomVideoRuntimeService) -> None:
        self.video_runtime_service = video_runtime_service
        self.room_service = RoomService()
        self.membership_service = RoomMembershipService()
        self.room_settings_service = RoomSettingsService()

    async def handle(
        self,
        *,
        db: AsyncSession,
        manager: RealtimeManager,
        publisher: RealtimePublisher,
        connection: WsConnection,
        command: WsCommandPayload,
    ) -> dict[str, Any] | None:
        room_id = self._require_active_room(connection)

        await self.room_service.get_room_by_id(db, room_id)

        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=connection.user_id,
        )
        if role is None:
            raise ForbiddenError("You are not allowed to control playback in this room")

        policy = await self._get_runtime_policy(db=db, room_id=room_id)

        self._require_active_sync_permission(
            role=role,
            permission=policy.active_sync_permission,
        )

        if command.action == WsCommandAction.PLAYBACK_SOURCE_SET:
            return await self._handle_source_set(
                db=db,
                publisher=publisher,
                room_id=room_id,
                command=command,
            )

        if command.action == WsCommandAction.PLAYBACK_PLAY:
            return await self._handle_play(
                publisher=publisher,
                room_id=room_id,
                command=command,
            )

        if command.action == WsCommandAction.PLAYBACK_PAUSE:
            return await self._handle_pause(
                publisher=publisher,
                room_id=room_id,
                command=command,
            )

        if command.action == WsCommandAction.PLAYBACK_SEEK:
            return await self._handle_seek(
                publisher=publisher,
                room_id=room_id,
                command=command,
            )

        raise BadRequestError(f"Unsupported playback command action: {command.action}")

    async def _handle_source_set(
        self,
        *,
        db: AsyncSession,
        publisher: RealtimePublisher,
        room_id: int,
        command: WsCommandPayload,
    ) -> dict[str, Any]:
        data = command.data or {}

        source_type = self._parse_source_type(data.get("source_type"))

        external_url: str | None = None
        file_hash: str | None = None

        if source_type == VideoSourceType.EXTERNAL_URL:
            external_url = self._parse_required_non_empty_string(
                data.get("external_url"),
                field_name="external_url",
            )
            if data.get("file_hash") is not None:
                raise BadRequestError("file_hash is not allowed for external_url source")
        else:
            file_hash = self._parse_required_non_empty_string(
                data.get("file_hash"),
                field_name="file_hash",
            )
            if data.get("external_url") is not None:
                raise BadRequestError("external_url is not allowed for local_file source")

        anchor_ts_ms = self._parse_optional_positive_int(
            data.get("anchor_ts_ms"),
            field_name="anchor_ts_ms",
        )

        await self._persist_selected_room_video_source_type(
            db=db,
            room_id=room_id,
            source_type=source_type,
        )

        video_source, playback = await self.video_runtime_service.set_video_source(
            room_id=room_id,
            source_type=source_type,
            external_url=external_url,
            file_hash=file_hash,
            anchor_ts_ms=anchor_ts_ms,
        )

        await publisher.publish_playback_source_set(video_source=video_source)
        await publisher.publish_playback_pause(playback=playback)

        return {
            "video_source": video_source.model_dump(mode="json"),
            "playback": playback.model_dump(mode="json"),
        }

    async def _handle_play(
        self,
        *,
        publisher: RealtimePublisher,
        room_id: int,
        command: WsCommandPayload,
    ) -> dict[str, Any]:
        data = command.data or {}

        position_seconds = self._parse_non_negative_number(
            data.get("position_seconds"),
            field_name="position_seconds",
        )
        anchor_ts_ms = self._parse_positive_int(
            data.get("anchor_ts_ms"),
            field_name="anchor_ts_ms",
        )
        playback_rate = self._parse_positive_number(
            data.get("playback_rate", 1.0),
            field_name="playback_rate",
        )

        playback = await self.video_runtime_service.play(
            room_id=room_id,
            position_seconds=position_seconds,
            anchor_ts_ms=anchor_ts_ms,
            playback_rate=playback_rate,
        )

        await publisher.publish_playback_play(playback=playback)
        return {
            "playback": playback.model_dump(mode="json"),
        }

    async def _handle_pause(
        self,
        *,
        publisher: RealtimePublisher,
        room_id: int,
        command: WsCommandPayload,
    ) -> dict[str, Any]:
        data = command.data or {}

        position_seconds = self._parse_non_negative_number(
            data.get("position_seconds"),
            field_name="position_seconds",
        )
        anchor_ts_ms = self._parse_positive_int(
            data.get("anchor_ts_ms"),
            field_name="anchor_ts_ms",
        )
        playback_rate = self._parse_positive_number(
            data.get("playback_rate", 1.0),
            field_name="playback_rate",
        )

        playback = await self.video_runtime_service.pause(
            room_id=room_id,
            position_seconds=position_seconds,
            anchor_ts_ms=anchor_ts_ms,
            playback_rate=playback_rate,
        )

        await publisher.publish_playback_pause(playback=playback)
        return {
            "playback": playback.model_dump(mode="json"),
        }

    async def _handle_seek(
        self,
        *,
        publisher: RealtimePublisher,
        room_id: int,
        command: WsCommandPayload,
    ) -> dict[str, Any]:
        data = command.data or {}

        position_seconds = self._parse_non_negative_number(
            data.get("position_seconds"),
            field_name="position_seconds",
        )
        anchor_ts_ms = self._parse_positive_int(
            data.get("anchor_ts_ms"),
            field_name="anchor_ts_ms",
        )

        playback = await self.video_runtime_service.seek(
            room_id=room_id,
            position_seconds=position_seconds,
            anchor_ts_ms=anchor_ts_ms,
        )

        await publisher.publish_playback_seek(playback=playback)
        return {
            "playback": playback.model_dump(mode="json"),
        }

    async def _persist_selected_room_video_source_type(
        self,
        *,
        db: AsyncSession,
        room_id: int,
        source_type: VideoSourceType,
    ) -> None:
        settings = await self.room_settings_service.find_room_settings_by_room_id(
            db,
            room_id=room_id,
        )
        if settings is None:
            settings = await self.room_settings_service.create_default_settings(
                db,
                room_id=room_id,
            )

        settings.selected_room_video_source_type = RoomMediaSourceType(source_type.value)
        await self.room_settings_service.repo.save_settings(db, settings)
        await db.commit()

    async def _get_runtime_policy(
        self,
        *,
        db: AsyncSession,
        room_id: int,
    ) -> PlaybackRuntimePolicy:
        settings = await self.room_settings_service.find_room_settings_by_room_id(
            db,
            room_id=room_id,
        )

        if settings is None:
            return PlaybackRuntimePolicy(
                sync_policy=RoomSyncPolicy.AUTO_PAUSE,
                active_sync_permission=RoomActiveSyncPermission.OWNER_AND_MANAGER,
            )

        return PlaybackRuntimePolicy(
            sync_policy=settings.sync_policy,
            active_sync_permission=settings.active_sync_permission,
        )

    @staticmethod
    def _require_active_room(connection: WsConnection) -> int:
        room_id = connection.active_room_id
        if room_id is None:
            raise BadRequestError("You must enter a room before controlling playback")
        return room_id

    @staticmethod
    def _require_active_sync_permission(
        *,
        role: RoomRole,
        permission: RoomActiveSyncPermission,
    ) -> None:
        if permission == RoomActiveSyncPermission.ALL_MEMBERS:
            return

        if permission == RoomActiveSyncPermission.OWNER_AND_MANAGER:
            if role in {RoomRole.OWNER, RoomRole.MANAGER}:
                return
            raise ForbiddenError("You do not have permission to control playback")

        if permission == RoomActiveSyncPermission.OWNER_ONLY:
            if role == RoomRole.OWNER:
                return
            raise ForbiddenError("You do not have permission to control playback")

        raise ForbiddenError("You do not have permission to control playback")

    @staticmethod
    def _parse_source_type(value: Any) -> VideoSourceType:
        if not isinstance(value, str):
            raise BadRequestError("source_type is required")

        try:
            return VideoSourceType(value)
        except ValueError as exc:
            raise BadRequestError("Invalid source_type") from exc

    @staticmethod
    def _parse_required_non_empty_string(value: Any, *, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise BadRequestError(f"{field_name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _parse_optional_positive_int(value: Any, *, field_name: str) -> int | None:
        if value is None:
            return None
        return PlaybackCommandHandler._parse_positive_int(value, field_name=field_name)

    @staticmethod
    def _parse_positive_int(value: Any, *, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise BadRequestError(f"{field_name} must be a positive integer")
        return value

    @staticmethod
    def _parse_non_negative_number(value: Any, *, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise BadRequestError(f"{field_name} must be a non-negative number")
        return float(value)

    @staticmethod
    def _parse_positive_number(value: Any, *, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise BadRequestError(f"{field_name} must be a positive number")
        return float(value)