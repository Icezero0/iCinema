import json

import pytest

from app.core.exceptions import ForbiddenError
from app.modules.media.constants import MediaAssetType
from app.modules.messages.schemas import MessageContentIn, MessageCreate
from app.modules.messages.service import MessageService


# 验证创建消息时会校验混合内容并记录媒体和表情使用。
async def test_create_message_persists_assets_and_emoji_usage(
    db_session,
    factories,
    monkeypatch,
) -> None:
    owner = await factories.create_user()
    room = await factories.create_room(owner=owner)
    image = await factories.create_media_asset(
        asset_type=MediaAssetType.IMAGE,
        uploaded_by=owner,
    )
    sticker = await factories.create_media_asset(
        asset_type=MediaAssetType.STICKER,
        uploaded_by=owner,
    )
    await factories.add_sticker_to_library(user=owner, asset=sticker, sort_order=1)
    await factories.commit()

    service = MessageService()

    async def fake_get_emoji_or_raise(emoji_id: str) -> dict:
        return {"id": emoji_id}

    touched_emoji_ids: list[str] = []

    async def fake_touch(*args, user_id: int, emoji_id: str, **kwargs) -> None:
        touched_emoji_ids.append(emoji_id)

    monkeypatch.setattr(service.media_service, "get_emoji_or_raise", fake_get_emoji_or_raise)
    monkeypatch.setattr(service.media_service, "touch_user_emoji_usage_in_tx", fake_touch)

    payload = MessageCreate(
        content=MessageContentIn.model_validate(
            {
                "segments": [
                    {"type": "text", "text": "hello"},
                    {"type": "emoji", "id": "smile"},
                    {"type": "emoji", "id": "smile"},
                    {"type": "image", "id": image.id},
                    {"type": "sticker", "id": sticker.id},
                ]
            }
        )
    )

    message = await service.create_message(
        db_session,
        room_id=room.id,
        user=owner,
        payload=payload,
    )

    assert message.sender_user_id == owner.id
    assert touched_emoji_ids == ["smile"]
    assert [segment.type for segment in message.content.segments] == [
        "text",
        "emoji",
        "emoji",
        "image",
        "sticker",
    ]


# 验证不具备房间权限的用户无法创建消息。
async def test_create_message_rejects_user_without_room_access(db_session, factories) -> None:
    owner = await factories.create_user()
    outsider = await factories.create_user()
    room = await factories.create_room(owner=owner)
    await factories.commit()

    with pytest.raises(ForbiddenError, match="You do not have permission"):
        await MessageService().create_message(
            db_session,
            room_id=room.id,
            user=outsider,
            payload=MessageCreate.model_validate(
                {"content": {"segments": [{"type": "text", "text": "hello"}]}}
            ),
        )


# 验证消息列表返回按时间正序输出，并带有分页游标。
async def test_get_messages_returns_oldest_first_and_sets_next_before_id(
    db_session,
    factories,
) -> None:
    owner = await factories.create_user()
    room = await factories.create_room(owner=owner)
    first = await factories.create_message(
        room=room,
        sender=owner,
        content=json.dumps({"segments": [{"type": "text", "text": "1"}]}),
    )
    second = await factories.create_message(
        room=room,
        sender=owner,
        content=json.dumps({"segments": [{"type": "text", "text": "2"}]}),
    )
    third = await factories.create_message(
        room=room,
        sender=owner,
        content=json.dumps({"segments": [{"type": "text", "text": "3"}]}),
    )
    await factories.commit()

    data = await MessageService().get_messages(
        db_session,
        room_id=room.id,
        user=owner,
        limit=2,
    )

    assert first.id < second.id < third.id
    assert [item.id for item in data.items] == [second.id, third.id]
    assert data.next_before_id == second.id
