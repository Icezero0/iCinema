from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_reasons import ErrorReason
from app.core.exceptions import BadRequestError, ForbiddenError
from app.core.logging import log_extra
from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomRole,
    RoomSyncPolicy,
    RoomVideoSourceType,
)
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.room.service import RoomService
from app.modules.rooms.settings.service import RoomSettingsService
from app.realtime.constants import AutoPlaybackAction, ResourceHealthStatusType, WsCommandAction
from app.realtime.manager import RealtimeManager, WsConnection
from app.realtime.protocol import WsCommandPayload
from app.realtime.publisher import RealtimePublisher
from app.realtime.room_video_runtime import RoomVideoRuntimeService

logger = logging.getLogger("app.realtime.video")


@dataclass
class RoomVideoRuntimePolicy:
    sync_policy: RoomSyncPolicy
    active_sync_permission: RoomActiveSyncPermission


class RoomVideoCommandHandler:
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
            raise ForbiddenError(
                "You are not allowed to control room video in this room",
                reason=ErrorReason.ROOM_VIDEO_CONTROL_FORBIDDEN,
                details={"room_id": room_id},
            )

        policy = await self._get_runtime_policy(db=db, room_id=room_id)

        if command.action == WsCommandAction.USER_RESOURCE_STATUS:
            return await self._handle_user_resource_status(
                publisher=publisher,
                room_id=room_id,
                user_id=connection.user_id,
                command=command,
                sync_policy=policy.sync_policy,
            )

        self._require_active_sync_permission(
            role=role,
            permission=policy.active_sync_permission,
        )

        if command.action == WsCommandAction.ROOM_VIDEO_SOURCE_SET:
            return await self._handle_room_video_source_set(
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
                sync_policy=policy.sync_policy,
            )

        if command.action == WsCommandAction.PLAYBACK_PAUSE:
            return await self._handle_pause(
                publisher=publisher,
                room_id=room_id,
                command=command,
                sync_policy=policy.sync_policy,
            )

        if command.action == WsCommandAction.PLAYBACK_SEEK:
            return await self._handle_seek(
                publisher=publisher,
                room_id=room_id,
                command=command,
                sync_policy=policy.sync_policy,
            )

        raise BadRequestError(
            f"Unsupported room video command action: {command.action}",
            reason=ErrorReason.UNSUPPORTED_ROOM_VIDEO_COMMAND_ACTION,
            details={"action": command.action},
        )

    async def _handle_room_video_source_set(
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

        if source_type == RoomVideoSourceType.EXTERNAL_URL:
            external_url = self._parse_required_non_empty_string(
                data.get("external_url"),
                field_name="external_url",
            )
            if data.get("file_hash") is not None:
                raise BadRequestError(
                    "file_hash is not allowed for external_url source",
                    reason=ErrorReason.FIELD_NOT_ALLOWED_FOR_SOURCE_TYPE,
                    details={
                        "field": "file_hash",
                        "source_type": source_type,
                    },
                )
        else:
            file_hash = self._parse_required_non_empty_string(
                data.get("file_hash"),
                field_name="file_hash",
            )
            if data.get("external_url") is not None:
                raise BadRequestError(
                    "external_url is not allowed for local_file source",
                    reason=ErrorReason.FIELD_NOT_ALLOWED_FOR_SOURCE_TYPE,
                    details={
                        "field": "external_url",
                        "source_type": source_type,
                    },
                )

        anchor_ts_ms = self._parse_optional_positive_int(
            data.get("anchor_ts_ms"),
            field_name="anchor_ts_ms",
        )

        await self.room_settings_service.set_selected_room_video_source_type(
            db,
            room_id=room_id,
            source_type=source_type,
        )

        room_video_source, playback, user_resource_states = (
            await self.video_runtime_service.set_room_video_source(
                room_id=room_id,
                source_type=source_type,
                external_url=external_url,
                file_hash=file_hash,
                anchor_ts_ms=anchor_ts_ms,
            )
        )

        logger.info(
            "room video source set: room_id=%s source_type=%s",
            room_id,
            source_type,
            **log_extra(
                "ws.video_source_set",
                room_id=room_id,
                source_type=source_type,
            ),
        )

        await publisher.publish_room_video_source_set(room_video_source=room_video_source)
        await publisher.publish_playback_pause(playback=playback)
        await publisher.publish_user_resource_states(user_resource_states=user_resource_states)

        return {
            "room_video_source": room_video_source.model_dump(mode="json"),
            "playback": playback.model_dump(mode="json"),
            "user_resource_states": user_resource_states.model_dump(mode="json"),
        }

    async def _handle_play(
        self,
        *,
        publisher: RealtimePublisher,
        room_id: int,
        command: WsCommandPayload,
        sync_policy: RoomSyncPolicy,
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
            sync_policy=sync_policy,
            playback_rate=playback_rate,
        )

        logger.info(
            "playback play: room_id=%s position_seconds=%s playback_rate=%s",
            room_id,
            position_seconds,
            playback_rate,
            **log_extra(
                "ws.playback_play",
                room_id=room_id,
                position_seconds=position_seconds,
                playback_rate=playback_rate,
            ),
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
        sync_policy: RoomSyncPolicy,
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
            sync_policy=sync_policy,
            playback_rate=playback_rate,
        )

        logger.info(
            "playback pause: room_id=%s position_seconds=%s playback_rate=%s",
            room_id,
            position_seconds,
            playback_rate,
            **log_extra(
                "ws.playback_pause",
                room_id=room_id,
                position_seconds=position_seconds,
                playback_rate=playback_rate,
            ),
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
        sync_policy: RoomSyncPolicy,
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
            sync_policy=sync_policy,
        )

        logger.info(
            "playback seek: room_id=%s position_seconds=%s",
            room_id,
            position_seconds,
            **log_extra(
                "ws.playback_seek",
                room_id=room_id,
                position_seconds=position_seconds,
            ),
        )

        await publisher.publish_playback_seek(playback=playback)
        return {
            "playback": playback.model_dump(mode="json"),
        }

    async def _handle_user_resource_status(
        self,
        *,
        publisher: RealtimePublisher,
        room_id: int,
        user_id: int,
        command: WsCommandPayload,
        sync_policy: RoomSyncPolicy,
    ) -> dict[str, Any]:
        data = command.data or {}

        status = self._parse_resource_health_status(data.get("status"))
        reported_at_ms = self._parse_positive_int(
            data.get("reported_at_ms"),
            field_name="reported_at_ms",
        )
        position_seconds = self._parse_optional_non_negative_number(
            data.get("position_seconds"),
            field_name="position_seconds",
        )
        error_code = self._parse_optional_string(
            data.get("error_code"),
            field_name="error_code",
        )
        error_message = self._parse_optional_string(
            data.get("error_message"),
            field_name="error_message",
        )

        result = await self.video_runtime_service.report_user_resource_status(
            room_id=room_id,
            user_id=user_id,
            status=status,
            reported_at_ms=reported_at_ms,
            sync_policy=sync_policy,
            position_seconds=position_seconds,
            error_code=error_code,
            error_message=error_message,
        )

        logger.info(
            "user resource status: room_id=%s user_id=%s status=%s sync_policy=%s",
            room_id,
            user_id,
            status,
            sync_policy,
            **log_extra(
                "ws.user_resource_status",
                user_id=user_id,
                room_id=room_id,
                status=status,
                sync_policy=sync_policy,
            ),
        )

        await publisher.publish_user_resource_states(
            user_resource_states=result.user_resource_states,
        )

        if result.auto_action == AutoPlaybackAction.PAUSE and result.auto_playback is not None:
            await publisher.publish_playback_pause(playback=result.auto_playback)
        elif result.auto_action == AutoPlaybackAction.PLAY and result.auto_playback is not None:
            await publisher.publish_playback_play(playback=result.auto_playback)

        response: dict[str, Any] = {
            "user_resource_states": result.user_resource_states.model_dump(mode="json")
        }
        if result.auto_playback is not None:
            response["playback"] = result.auto_playback.model_dump(mode="json")
            response["auto_action"] = result.auto_action.value
        return response

    async def _get_runtime_policy(
        self,
        *,
        db: AsyncSession,
        room_id: int,
    ) -> RoomVideoRuntimePolicy:
        settings = await self.room_settings_service.find_room_settings_by_room_id(
            db,
            room_id=room_id,
        )

        if settings is None:
            return RoomVideoRuntimePolicy(
                sync_policy=RoomSyncPolicy.AUTO_SYNC,
                active_sync_permission=RoomActiveSyncPermission.OWNER_AND_MANAGER,
            )

        return RoomVideoRuntimePolicy(
            sync_policy=settings.sync_policy,
            active_sync_permission=settings.active_sync_permission,
        )

    @staticmethod
    def _require_active_room(connection: WsConnection) -> int:
        room_id = connection.active_room_id
        if room_id is None:
            raise BadRequestError(
                "You must enter a room before controlling room video",
                reason=ErrorReason.ROOM_NOT_ENTERED,
            )
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
            raise ForbiddenError(
                "You do not have permission to control room video",
                reason=ErrorReason.ROOM_VIDEO_CONTROL_PERMISSION_DENIED,
                details={
                    "role": role,
                    "required_permission": permission,
                },
            )

        if permission == RoomActiveSyncPermission.OWNER_ONLY:
            if role == RoomRole.OWNER:
                return
            raise ForbiddenError(
                "You do not have permission to control room video",
                reason=ErrorReason.ROOM_VIDEO_CONTROL_PERMISSION_DENIED,
                details={
                    "role": role,
                    "required_permission": permission,
                },
            )

        raise ForbiddenError(
            "You do not have permission to control room video",
            reason=ErrorReason.ROOM_VIDEO_CONTROL_PERMISSION_DENIED,
            details={
                "role": role,
                "required_permission": permission,
            },
        )

    @staticmethod
    def _parse_source_type(value: Any) -> RoomVideoSourceType:
        if not isinstance(value, str):
            raise BadRequestError(
                "source_type is required",
                reason=ErrorReason.MISSING_SOURCE_TYPE,
                details={"field": "source_type", "constraint": "required"},
            )

        try:
            return RoomVideoSourceType(value)
        except ValueError as exc:
            raise BadRequestError(
                "Invalid source_type",
                reason=ErrorReason.INVALID_SOURCE_TYPE,
                details={
                    "field": "source_type",
                    "allowed_values": [item.value for item in RoomVideoSourceType],
                },
            ) from exc

    @staticmethod
    def _parse_resource_health_status(value: Any) -> ResourceHealthStatusType:
        if not isinstance(value, str):
            raise BadRequestError(
                "status is required",
                reason=ErrorReason.MISSING_RESOURCE_HEALTH_STATUS,
                details={"field": "status", "constraint": "required"},
            )

        try:
            return ResourceHealthStatusType(value)
        except ValueError as exc:
            raise BadRequestError(
                "Invalid status",
                reason=ErrorReason.INVALID_RESOURCE_HEALTH_STATUS,
                details={
                    "field": "status",
                    "allowed_values": [item.value for item in ResourceHealthStatusType],
                },
            ) from exc

    @staticmethod
    def _parse_required_non_empty_string(value: Any, *, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise BadRequestError(
                f"{field_name} must be a non-empty string",
                reason=ErrorReason.INVALID_STRING_FIELD,
                details={
                    "field": field_name,
                    "constraint": "non_empty_string",
                },
            )
        return value.strip()

    @staticmethod
    def _parse_optional_string(value: Any, *, field_name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise BadRequestError(
                f"{field_name} must be a string",
                reason=ErrorReason.INVALID_STRING_FIELD,
                details={"field": field_name, "constraint": "string"},
            )
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _parse_optional_positive_int(value: Any, *, field_name: str) -> int | None:
        if value is None:
            return None
        return RoomVideoCommandHandler._parse_positive_int(value, field_name=field_name)

    @staticmethod
    def _parse_positive_int(value: Any, *, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise BadRequestError(
                f"{field_name} must be a positive integer",
                reason=ErrorReason.INVALID_INTEGER_FIELD,
                details={
                    "field": field_name,
                    "constraint": "positive_integer",
                },
            )
        return value

    @staticmethod
    def _parse_optional_non_negative_number(
        value: Any,
        *,
        field_name: str,
    ) -> float | None:
        if value is None:
            return None
        return RoomVideoCommandHandler._parse_non_negative_number(
            value,
            field_name=field_name,
        )

    @staticmethod
    def _parse_non_negative_number(value: Any, *, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise BadRequestError(
                f"{field_name} must be a non-negative number",
                reason=ErrorReason.INVALID_NUMBER_FIELD,
                details={
                    "field": field_name,
                    "constraint": "non_negative_number",
                },
            )
        return float(value)

    @staticmethod
    def _parse_positive_number(value: Any, *, field_name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise BadRequestError(
                f"{field_name} must be a positive number",
                reason=ErrorReason.INVALID_NUMBER_FIELD,
                details={
                    "field": field_name,
                    "constraint": "positive_number",
                },
            )
        return float(value)
