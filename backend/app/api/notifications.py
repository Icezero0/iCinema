from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from .. import crud, schemas
from ..database import get_db
from .users import get_current_user

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from .. import crud, models, schemas

router = APIRouter()

@router.get("/notifications/", response_model=schemas.NotificationList)
async def read_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, description="通知状态筛选，如'unread', 'read'等"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取当前用户的通知列表，支持分页和状态筛选
    """
    
    notification_list = await crud.notifications.get_notification_list_by_userid(
        db=db, 
        user_id=int(current_user.id),
        status=status,
        skip=skip, 
        limit=limit
    )

    return notification_list