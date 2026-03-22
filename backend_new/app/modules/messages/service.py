import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.media.constants import MediaAssetStatus, MediaAssetType
from app.modules.media.service import MediaService
from app.modules.messages.models import Message
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import (
    EmojiSegmentOut,
    ImageSegmentOut,
    MessageContentIn,
    MessageContentOut,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    StickerSegmentOut,
    TextSegmentOut,
)
from app.modules.rooms.constants import RoomPermission
from app.modules.rooms.membership.service import RoomMembershipService
from app.modules.rooms.permissions import require_room_permission
from app.modules.rooms.room.service import RoomService
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse
from app.modules.users.service import UserService


class MessageService:
    def __init__(self) -> None:
        self.repo = MessageRepository()
        self.media_service = MediaService()
        self.room_service = RoomService()
        self.membership_service = RoomMembershipService()
        self.user_service = UserService()

    async def create_message(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        payload: MessageCreate,
    ) -> MessageResponse:
        await self._require_room_permission(
            db,
            room_id=room_id,
            user_id=user.id,
            permission=RoomPermission.SEND_MESSAGE,
        )

        content = self._dump_content(payload.content)

        message = await self.repo.create_message(
            db,
            content=content,
            sender_user_id=user.id,
            room_id=room_id,
        )
        await db.commit()

        message = await self.repo.find_message_by_id(db, message.id)
        if message is None:
            raise NotFoundError("Message not found")

        if message.sender is not None:
            await self.user_service.hydrate_user_avatar_key(db, message.sender)

        return await self._build_message_response(db, message)

    async def get_messages(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user: User,
        before_id: int | None = None,
        limit: int = 20,
    ) -> MessageListResponse:
        await self._require_room_permission(
            db,
            room_id=room_id,
            user_id=user.id,
            permission=RoomPermission.VIEW_MESSAGES,
        )

        messages = await self.repo.get_messages_by_room_id(
            db,
            room_id=room_id,
            before_id=before_id,
            limit=limit,
        )

        senders = []
        seen_user_ids: set[int] = set()
        for message in messages:
            if message.sender is None:
                continue
            if message.sender.id in seen_user_ids:
                continue
            seen_user_ids.add(message.sender.id)
            senders.append(message.sender)

        await self.user_service.hydrate_users_avatar_key(db, senders)

        next_before_id = messages[-1].id if len(messages) == limit else None

        items = []
        for message in reversed(messages):
            items.append(await self._build_message_response(db, message))

        return MessageListResponse(
            items=items,
            next_before_id=next_before_id,
        )

    async def _require_room_permission(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        user_id: int,
        permission: RoomPermission,
    ) -> None:
        await self.room_service.get_room_by_id(db, room_id)

        role = await self.membership_service.find_room_role(
            db,
            room_id=room_id,
            user_id=user_id,
        )
        if role is None:
            raise ForbiddenError("You do not have permission to perform this action")

        require_room_permission(role, permission)

    def _dump_content(self, content: MessageContentIn) -> str:
        return json.dumps(content.model_dump(mode="json"), ensure_ascii=False)

    def _load_content(self, raw_content: str) -> MessageContentOut:
        data = json.loads(raw_content)
        segments = []

        for segment in data["segments"]:
            segment_type = segment["type"]

            if segment_type == "text":
                segments.append(TextSegmentOut(**segment))
            elif segment_type == "emoji":
                segments.append(EmojiSegmentOut(**segment))
            elif segment_type == "image":
                segments.append(ImageSegmentOut(**segment))
            elif segment_type == "sticker":
                segments.append(StickerSegmentOut(**segment))
            else:
                raise ValueError(f"Unsupported segment type: {segment_type}")

        return MessageContentOut(segments=segments)

    async def _build_message_response(
        self,
        db: AsyncSession,
        message: Message,
    ) -> MessageResponse:

        content = self._load_content(message.content)
        content = await self._enrich_content_urls(db, content)

        return MessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_user_id=message.sender_user_id,
            sender=UserResponse.model_validate(message.sender) if message.sender is not None else None,
            content=content,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    async def _enrich_content_urls(
        self,
        db: AsyncSession,
        content: MessageContentOut,
    ) -> MessageContentOut:
        asset_ids: set[int] = set()

        for segment in content.segments:
            if isinstance(segment, (ImageSegmentOut, StickerSegmentOut)):
                asset_ids.add(segment.id)

        if not asset_ids:
            return content

        assets = await self.media_service.get_media_assets_by_ids(
            db,
            list(asset_ids),
        )
        asset_map = {asset.id: asset for asset in assets}

        for segment in content.segments:
            if isinstance(segment, ImageSegmentOut):
                asset = asset_map.get(segment.id)
                if (
                    asset
                    and asset.asset_type == MediaAssetType.IMAGE
                    and not self.media_service.is_asset_expired(asset)
                ):
                    segment.url = self.media_service.get_media_asset_url(asset)

            elif isinstance(segment, StickerSegmentOut):
                asset = asset_map.get(segment.id)
                if (
                    asset
                    and asset.asset_type == MediaAssetType.STICKER
                    and asset.status == MediaAssetStatus.ACTIVE
                ):
                    segment.url = self.media_service.get_media_asset_url(asset)

        return content