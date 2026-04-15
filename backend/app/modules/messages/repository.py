from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.media.models import MessageResourceRef
from app.modules.messages.models import Message


class MessageRepository:
    async def create_message(
        self,
        db: AsyncSession,
        *,
        content: str,
        sender_user_id: int,
        room_id: int,
    ) -> Message:
        message = Message(
            content=content,
            sender_user_id=sender_user_id,
            room_id=room_id,
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    async def create_message_resource_refs(
        self,
        db: AsyncSession,
        *,
        message_id: int,
        media_asset_ids: list[int],
    ) -> None:
        if not media_asset_ids:
            return

        rows = [
            MessageResourceRef(
                message_id=message_id,
                media_asset_id=media_asset_id,
            )
            for media_asset_id in media_asset_ids
        ]
        db.add_all(rows)
        await db.flush()

    async def find_message_by_id(
        self,
        db: AsyncSession,
        message_id: int,
    ) -> Message | None:
        result = await db.execute(
            select(Message)
            .where(Message.id == message_id)
            .options(selectinload(Message.sender))
        )
        return result.scalar_one_or_none()

    async def get_messages_by_room_id(
        self,
        db: AsyncSession,
        *,
        room_id: int,
        before_id: int | None = None,
        limit: int = 20,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.room_id == room_id)
            .options(selectinload(Message.sender))
            .order_by(desc(Message.id))
            .limit(limit)
        )

        if before_id is not None:
            stmt = stmt.where(Message.id < before_id)

        result = await db.execute(stmt)
        return list(result.scalars().all())