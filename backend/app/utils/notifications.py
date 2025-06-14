import json
import secrets


def create_notification_content(
    room_id: int, 
    user_id: int, 
    type: str,
    need_token: bool = True
):
    """
    创建通知内容的工具函数
    
    Args:
        room_id: 房间ID
        user_id: 用户ID
        type: 通知类型 (owner_invitation, join_request, member_invitation)
    
    Returns:
        str: JSON格式的通知内容字符串
    """
    if need_token:
        token = secrets.token_urlsafe(16)
        content_data = {
            "room_id": room_id,
            "user_id": user_id,
            "type": type,
            "token": token
        }
    else:
        content_data = {
            "room_id": room_id,
            "user_id": user_id,
            "type": type
        }
    return json.dumps(content_data)
