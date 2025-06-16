import json
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from .. import crud, models, schemas
from ..database import get_db
from ..utils.notifications import create_notification_content 
from app.auth.dependencies import get_current_user

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
    
    db_notifications , total = await crud.notifications.get_notification_list_by_userid(
        db=db, 
        user_id=int(current_user.id),
        status=status,
        skip=skip, 
        limit=limit
    )

    notifications = [
        schemas.NotificationResponse.model_validate(notification) for notification in db_notifications
    ]
    
    return schemas.NotificationListResponse(
        items=list(notifications),
        total=total
    )


@router.post("/notifications/{notification_id}/respond", status_code=status.HTTP_200_OK)
async def respond_to_notification(
    notification_id: int,
    response_action: schemas.NotificationAction,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """
    处理用户对邀请或申请通知的响应 (接受/拒绝)
    """
    # 1. 获取通知
    db_notification = await crud.notifications.get_notification(db, notification_id)

    if not db_notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    schema_notification = schemas.Notification.model_validate(db_notification)

    # 2. 检查该通知是否已经被删除
    if schema_notification.is_deleted:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="通知已被删除")

    # 3. 权限校验：确保当前用户是通知的接收者
    if schema_notification.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限操作此通知")

    # 4. 检查通知状态是否可处理 (例如 "pending")
    if schema_notification.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"通知状态为 '{schema_notification.status}'，无法处理"
        )

    # 5. 解析通知内容
    try:
        content_data = json.loads(schema_notification.content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="通知内容格式错误")
    
    notification_type = content_data.get("type")
    if not notification_type:
        # 如果没有类型，可能是旧通知或格式错误
        await crud.notifications.update_notification(db, notification_id, status="error_no_type", is_deleted=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="通知内容缺少类型信息")

    # 6.判断通知类型，根据类型进行相应处理
    if notification_type in ["owner_invitation", "member_invitation", "join_request"]:
        target_room_id = content_data.get("room_id")
        target_user_id = content_data.get("user_id")

        if not all([target_room_id, target_user_id]):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="通知内容不完整")

        db_target_room = await crud.rooms.get_room(db, target_room_id)
        if not db_target_room:
            await crud.notifications.update_notification(db, notification_id, status="error_room_not_found", is_deleted=True)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"房间 {target_room_id} 不存在")
        target_room = schemas.Room.model_validate(db_target_room)
        
        if notification_type == "owner_invitation":
            # 房主邀请用户加入房间
            token = content_data.get("token")
            if not token:
                await crud.notifications.update_notification(db, notification_id, status="error_invalid_token", is_deleted=True)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该通知缺少令牌")
            # 验证令牌是否一致
            if response_action.token != token:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无效的令牌")
            # 处理房主邀请的逻辑
            if response_action.action == "accept":
                # 检查用户是否已在房间
                is_member = await crud.rooms.is_room_member(db, target_room_id, target_user_id)
                if is_member:
                    await crud.notifications.update_notification(db, notification_id, status="already_in_room", is_deleted=True)
                    return {"message": "用户已经在该房间中了"}
                await crud.rooms.add_room_member(db, target_room_id, target_user_id)
                await crud.notifications.update_notification(db, notification_id, status="accepted", is_deleted=True)
                return {"message": "邀请已接受，用户已添加到房间"}
            elif response_action.action == "reject":
                await crud.notifications.update_notification(db, notification_id, status="rejected", is_deleted=True)
                return {"message": "邀请已拒绝"}
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效操作")


        elif notification_type == "member_invitation":
            # 成员邀请用户加入房间
            if response_action.action == "accept":
                is_member = await crud.rooms.is_room_member(db, target_room_id, target_user_id)
                if is_member:
                    await crud.notifications.update_notification(db, notification_id, status="already_in_room", is_deleted=True)
                    return {"message": "用户已经在该房间中了"}
                await crud.notifications.create_notification(db, recipient_id=target_room.owner_id,
                    sender_id=current_user.id, 
                    content=create_notification_content(
                        room_id=target_room_id,
                        user_id=target_user_id,
                        type="join_request"
                    ),
                    status="pending"
                )
                await crud.notifications.update_notification(db, notification_id, status="accepted", is_deleted=True)
                return {"message": "邀请已接受，等待房主确认"}
            elif response_action.action == "reject":
                await crud.notifications.update_notification(db, notification_id, status="rejected", is_deleted=True)
                return {"message": "邀请已拒绝"}
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效操作")
            
        elif notification_type == "join_request":   
            # 用户申请加入房间
            token = content_data.get("token")
            if not token:
                await crud.notifications.update_notification(db, notification_id, status="error_invalid_token", is_deleted=True)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该通知缺少令牌")
            # 验证令牌是否一致
            if response_action.token != token:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无效的令牌")
            # 处理用户申请加入的逻辑
            if response_action.action == "accept":
                is_member = await crud.rooms.is_room_member(db, target_room_id, target_user_id)
                if is_member:
                    await crud.notifications.update_notification(db, notification_id, status="already_in_room", is_deleted=True)
                    return {"message": "用户已经在该房间中了"}
                await crud.rooms.add_room_member(db, target_room_id, target_user_id)
                await crud.notifications.update_notification(db, notification_id, status="accepted", is_deleted=True)
                return {"message": "邀请已接受，用户已添加到房间"}
            elif response_action.action == "reject":
                await crud.notifications.update_notification(db, notification_id, status="rejected", is_deleted=True)
                return {"message": "邀请已拒绝"}
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效操作")
    else:
        # 未知类型，更新通知状态并返回错误
        await crud.notifications.update_notification(db, notification_id, status="error_unknown_type", is_deleted=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知的通知类型: {notification_type}")

@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_notification = await crud.notifications.get_notification(db, notification_id)
    if not db_notification or bool(db_notification.is_deleted):
        raise HTTPException(status_code=404, detail="通知不存在")
    # 只能删除属于自己的通知
    if db_notification.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除该通知")
    updated = await crud.notifications.update_notification(db, notification_id, is_deleted=True)
    if not updated:
        raise HTTPException(status_code=400, detail="删除失败")
    return None


