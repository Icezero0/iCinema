import os
import shutil
import sys
import tempfile
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
TEST_DATA_DIR = Path(tempfile.gettempdir()) / "icinema_backend_new_tests"
os.environ.setdefault("DATA_DIR", str(TEST_DATA_DIR))
os.environ["DEBUG"] = "false"

from app.core.database import AsyncSessionLocal, engine
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.core.startup import ensure_runtime_paths
from app.db.base import Base
from app.main import create_app
from app.modules.media.constants import (
    EmojiProvider,
    MediaAssetStatus,
    MediaAssetType,
    StickerLibrarySource,
)
from app.modules.media.models import (
    MediaAsset,
    MessageResourceRef,
    UserAvatarAsset,
    UserEmojiUsage,
    UserStickerLibraryItem,
)
from app.modules.feedback.models import Feedback, FeedbackScreenshot
from app.modules.feedback.constants import FeedbackPage, FeedbackStatus, FeedbackType
from app.modules.notifications.constants import NotificationType
from app.modules.notifications.models import Notification
from app.modules.rooms.constants import (
    RoomActiveSyncPermission,
    RoomJoinAuditMode,
    RoomJoinRequestAction,
    RoomJoinRequestSource,
    RoomJoinRequestStatus,
    RoomRole,
    RoomSyncPolicy,
    RoomVideoSourceType,
    RoomVisibility,
)
from app.modules.rooms.models import Room, RoomJoinRequest, RoomMember, RoomSettings
from app.modules.users.models import User
from app.modules.messages.models import Message
from app.modules.site.constants import SiteRole


@pytest_asyncio.fixture(autouse=True)
async def prepare_test_database() -> AsyncIterator[None]:
    await ensure_runtime_paths()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def reset_database() -> AsyncIterator[None]:
    yield
    async with AsyncSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(delete(table))
        await session.commit()

    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    await ensure_runtime_paths()


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def app():
    return create_app()


@pytest_asyncio.fixture
async def api_client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    def _build(user: User) -> dict[str, str]:
        token = create_access_token(str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return _build


@pytest.fixture
def refresh_token_for() -> Callable[[User], str]:
    def _build(user: User) -> str:
        return create_refresh_token(str(user.id))

    return _build


@pytest_asyncio.fixture
async def factories(db_session):
    counters = {
        "user": 0,
        "room": 0,
        "asset": 0,
        "message": 0,
    }

    async def create_user(
        *,
        email: str | None = None,
        username: str | None = None,
        password: str = "Password123",
        auto_accept: bool = False,
        site_role: SiteRole = SiteRole.USER,
    ) -> User:
        counters["user"] += 1
        user = User(
            email=email or f"user{counters['user']}@example.com",
            username=username or f"user-{counters['user']}",
            hashed_password=hash_password(password),
            auto_accept=auto_accept,
            site_role=site_role.value,
        )
        db_session.add(user)
        await db_session.flush()
        return user

    async def create_room(
        *,
        owner: User,
        name: str | None = None,
        visibility: RoomVisibility = RoomVisibility.PRIVATE,
        join_audit_mode: RoomJoinAuditMode = RoomJoinAuditMode.MANUAL_REVIEW,
        with_owner_member: bool = True,
        with_settings: bool = True,
    ) -> Room:
        counters["room"] += 1
        room = Room(
            name=name or f"Room {counters['room']}",
            owner_id=owner.id,
            visibility=visibility,
            join_audit_mode=join_audit_mode,
        )
        db_session.add(room)
        await db_session.flush()

        if with_owner_member:
            db_session.add(
                RoomMember(
                    room_id=room.id,
                    user_id=owner.id,
                    role=RoomRole.OWNER.value,
                )
            )

        if with_settings:
            db_session.add(
                RoomSettings(
                    room_id=room.id,
                    selected_room_video_source_type=RoomVideoSourceType.EXTERNAL_URL,
                    sync_policy=RoomSyncPolicy.AUTO_SYNC,
                    active_sync_permission=RoomActiveSyncPermission.OWNER_AND_MANAGER,
                )
            )

        await db_session.flush()
        return room

    async def add_member(
        *,
        room: Room,
        user: User,
        role: RoomRole = RoomRole.MEMBER,
    ) -> RoomMember:
        member = RoomMember(room_id=room.id, user_id=user.id, role=role.value)
        db_session.add(member)
        await db_session.flush()
        return member

    async def create_join_request(
        *,
        room: Room,
        initiator: User,
        target: User,
        source: RoomJoinRequestSource = RoomJoinRequestSource.APPLY,
        status: RoomJoinRequestStatus = RoomJoinRequestStatus.PENDING,
        room_action: RoomJoinRequestAction = RoomJoinRequestAction.PENDING,
        target_action: RoomJoinRequestAction = RoomJoinRequestAction.PENDING,
        room_action_by_user_id: int | None = None,
    ) -> RoomJoinRequest:
        request = RoomJoinRequest(
            room_id=room.id,
            initiator_user_id=initiator.id,
            target_user_id=target.id,
            source=source,
            status=status,
            room_action=room_action,
            target_action=target_action,
            room_action_by_user_id=room_action_by_user_id,
        )
        db_session.add(request)
        await db_session.flush()
        return request

    async def create_notification(
        *,
        recipient: User,
        actor: User | None = None,
        notification_type: NotificationType = NotificationType.WORKFLOW,
        related_type=None,
        related_id: int | None = None,
        is_read: bool = False,
    ) -> Notification:
        notification = Notification(
            recipient_user_id=recipient.id,
            actor_user_id=actor.id if actor else None,
            notification_type=notification_type,
            related_type=related_type,
            related_id=related_id,
            is_read=is_read,
        )
        db_session.add(notification)
        await db_session.flush()
        return notification

    async def create_media_asset(
        *,
        asset_type: str = MediaAssetType.IMAGE,
        uploaded_by: User | None = None,
        status: str = MediaAssetStatus.ACTIVE,
        storage_key: str | None = None,
        sha256: str | None = None,
        expires_at=None,
    ) -> MediaAsset:
        counters["asset"] += 1
        asset = MediaAsset(
            asset_type=asset_type,
            storage_key=storage_key or f"{asset_type}-{counters['asset']}.bin",
            mime_type="image/png",
            file_size=128,
            sha256=sha256 or f"sha-{asset_type}-{counters['asset']}",
            uploaded_by_user_id=uploaded_by.id if uploaded_by else None,
            status=status,
            expires_at=expires_at,
        )
        db_session.add(asset)
        await db_session.flush()
        return asset

    async def attach_avatar(*, user: User, asset: MediaAsset, is_deleted: bool = False) -> UserAvatarAsset:
        avatar_asset = UserAvatarAsset(
            user_id=user.id,
            media_asset_id=asset.id,
            is_deleted=is_deleted,
        )
        db_session.add(avatar_asset)
        await db_session.flush()
        return avatar_asset

    async def add_sticker_to_library(
        *,
        user: User,
        asset: MediaAsset,
        source: StickerLibrarySource = StickerLibrarySource.UPLOAD,
        sort_order: int = 1,
    ) -> UserStickerLibraryItem:
        item = UserStickerLibraryItem(
            user_id=user.id,
            media_asset_id=asset.id,
            source=source,
            sort_order=sort_order,
        )
        db_session.add(item)
        await db_session.flush()
        return item

    async def create_emoji_usage(
        *,
        user: User,
        emoji_id: str,
        provider: str = EmojiProvider.QFACE,
    ) -> UserEmojiUsage:
        usage = UserEmojiUsage(
            user_id=user.id,
            provider=provider,
            emoji_id=emoji_id,
        )
        db_session.add(usage)
        await db_session.flush()
        return usage

    async def create_message(
        *,
        room: Room,
        sender: User | None,
        content: str,
    ) -> Message:
        counters["message"] += 1
        message = Message(
            room_id=room.id,
            sender_user_id=sender.id if sender else None,
            content=content,
        )
        db_session.add(message)
        await db_session.flush()
        return message

    async def create_feedback(
        *,
        creator: User,
        feedback_type: FeedbackType = FeedbackType.BUG,
        page: FeedbackPage = FeedbackPage.ROOM,
        title: str = "Feedback title",
        description: str = "Feedback description",
        status: FeedbackStatus = FeedbackStatus.OPEN,
        screenshot_assets: list[MediaAsset] | None = None,
        handled_by: User | None = None,
        admin_note: str | None = None,
    ) -> Feedback:
        feedback = Feedback(
            creator_id=creator.id,
            handled_by_id=handled_by.id if handled_by else None,
            feedback_type=feedback_type.value,
            page=page.value,
            title=title,
            description=description,
            status=status.value,
            admin_note=admin_note,
        )
        db_session.add(feedback)
        await db_session.flush()

        for index, asset in enumerate(screenshot_assets or []):
            db_session.add(
                FeedbackScreenshot(
                    feedback_id=feedback.id,
                    asset_id=asset.id,
                    sort_order=index,
                )
            )
        if screenshot_assets:
            await db_session.flush()

        return feedback

    async def add_message_resource_ref(*, message: Message, asset: MediaAsset) -> MessageResourceRef:
        ref = MessageResourceRef(message_id=message.id, media_asset_id=asset.id)
        db_session.add(ref)
        await db_session.flush()
        return ref

    async def commit() -> None:
        await db_session.commit()

    async def refresh(instance) -> None:
        await db_session.refresh(instance)

    async def get(model, pk):
        return await db_session.get(model, pk)

    async def list_all(model):
        result = await db_session.execute(select(model))
        return list(result.scalars())

    factory_namespace = SimpleNamespace(
        create_user=create_user,
        create_room=create_room,
        add_member=add_member,
        create_join_request=create_join_request,
        create_notification=create_notification,
        create_media_asset=create_media_asset,
        attach_avatar=attach_avatar,
        add_sticker_to_library=add_sticker_to_library,
        create_emoji_usage=create_emoji_usage,
        create_message=create_message,
        create_feedback=create_feedback,
        add_message_resource_ref=add_message_resource_ref,
        commit=commit,
        refresh=refresh,
        get=get,
        list_all=list_all,
    )

    yield factory_namespace


@pytest.fixture
def sample_upload_bytes() -> bytes:
    return b"not-a-real-png-but-good-enough-for-tests"
