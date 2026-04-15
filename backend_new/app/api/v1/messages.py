from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_realtime_publisher
from app.core.database import get_db
from app.modules.auth.deps import get_current_user
from app.modules.messages.schemas import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
)
from app.modules.messages.service import MessageService
from app.modules.users.models import User
from app.realtime.publisher import RealtimePublisher

router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["messages"])

message_service = MessageService()


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    room_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    publisher: RealtimePublisher = Depends(get_realtime_publisher),
) -> MessageResponse:
    message = await message_service.create_message(
        db,
        room_id=room_id,
        user=current_user,
        payload=payload,
    )
    await publisher.publish_message(room_id=room_id, message=message)
    return message


@router.get("", response_model=MessageListResponse)
async def get_messages(
    room_id: int,
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageListResponse:
    return await message_service.get_messages(
        db,
        room_id=room_id,
        user=current_user,
        before_id=before_id,
        limit=limit,
    )
