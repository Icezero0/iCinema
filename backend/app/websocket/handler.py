from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect, status
from typing import Optional
from .manager import manager
from app.auth.utils import verify_token
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """
    WebSocket处理器
    
    职责：
    - 处理WebSocket协议层操作（accept/close）
    - 执行认证流程
    - 协调连接建立和消息处理
    - 调用ConnectionManager进行连接管理
    """
    # 认证超时时间（秒）
    AUTH_TIMEOUT = 30

    async def handle_connection(self, websocket: WebSocket):
        """处理WebSocket连接 - 支持Bearer token和连接后认证"""
        user_id = None
        
        # 方案1: 尝试从Headers获取Bearer token
        authorization = websocket.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            user_id = verify_token(token)
            if user_id:
                await websocket.accept()
                await self._handle_authenticated_connection(websocket, user_id)
                return
        
        # 方案2: 如果Headers认证失败，尝试连接后认证
        await websocket.accept()
        try:
            # 发送认证要求
            await websocket.send_json({
                "type": "auth_required",
                "payload": {
                    "message": "请发送认证令牌", 
                    "timeout": self.AUTH_TIMEOUT
                }
            })
            
            # 等待认证消息（带超时控制）
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=self.AUTH_TIMEOUT
            )
            token = auth_data.get("token")
            if not token:
                await websocket.send_json({
                    "type": "auth_error", 
                    "payload": {"message": "缺少认证令牌"}
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            user_id = verify_token(token)
            if not user_id:
                await websocket.send_json({
                    "type": "auth_error",
                    "payload": {"message": "无效的认证令牌"}
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            # 认证成功
            await websocket.send_json({
                "type": "auth_success",
                "payload": {"message": "认证成功", "user_id": user_id}
            })
            
            await self._handle_authenticated_connection(websocket, user_id)
            
        except asyncio.TimeoutError:
            # 认证超时处理
            await websocket.send_json({
                "type": "auth_error",
                "payload": {"message": f"认证超时（{self.AUTH_TIMEOUT}秒），连接将关闭"}
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning("WebSocket认证超时")
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "auth_error",
                "payload": {"message": "无效的JSON格式"}
            })
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        except WebSocketDisconnect:
            logger.info("用户在认证过程中断开连接")
        except Exception as e:
            logger.error(f"认证过程中发生错误: {e}")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    async def _handle_authenticated_connection(self, websocket: WebSocket, user_id: int):
        """处理已认证的WebSocket连接"""
        try:
            await manager.register_connection(websocket, user_id)
            
            # 发送连接确认
            await websocket.send_json({
                "type": "connection_established",
                "payload": {
                    "user_id": user_id,
                    "message": "WebSocket连接已建立"
                }
            })

            # 进入消息处理循环
            await self._message_loop(websocket, user_id)

        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            manager.disconnect(user_id)

    async def _message_loop(self, websocket: WebSocket, user_id: int):
        """已认证连接的消息处理循环"""
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                await self.process_message(websocket, user_id, message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "消息格式必须是有效的JSON"}
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Message processing error for user {user_id}: {e}")
                break

    async def process_message(self, websocket: WebSocket, user_id: int, message: dict):
        """处理收到的消息"""
        message_type = message.get("type")
        payload = message.get("payload", {})

        if message_type == "ping":
            # 心跳响应
            await websocket.send_json({
                "type": "pong"
            })
            
        elif message_type == "enter_room":
            # 进入房间（包含数据库验证）
            room_id = int(payload.get("room_id"))
            if room_id:
                try:
                    success = await manager.enter_room(user_id, room_id)
                    if success:
                        await websocket.send_json({
                            "type": "room_entered",
                            "payload": {
                                "room_id": room_id,
                                "status": "success",
                                "active_users": manager.get_room_active_users_count(room_id)
                            }
                        })
                    else:
                        await websocket.send_json({
                            "type": "room_enter_error",
                            "payload": {
                                "room_id": room_id,
                                "status": "failed",
                                "message": "无法进入房间，请检查房间是否存在或您是否有权限"
                            }
                        })
                except Exception as e:
                    logger.error(f"Error entering room {room_id} for user {user_id}: {e}")
                    await websocket.send_json({
                        "type": "room_enter_error",
                        "payload": {
                            "room_id": room_id,
                            "status": "error",
                            "message": "进入房间时发生错误"
                        }
                    })
            else:
                await websocket.send_json({
                    "type": "room_enter_error",
                    "payload": {
                        "status": "invalid",
                        "message": "缺少房间ID"
                    }
                })
            
        
        elif message_type == "leave_room":
            # 离开房间
            room_id = int(payload.get("room_id"))
            if room_id and room_id == manager.get_user_current_room(user_id):
                try:
                    await manager.leave_room(user_id, room_id)
                    await websocket.send_json({
                        "type": "room_left", 
                        "payload": {
                            "room_id": room_id,
                            "status": "success"
                        }
                    })
                except Exception as e:
                    logger.error(f"Error leaving room {room_id} for user {user_id}: {e}")
                    await websocket.send_json({
                        "type": "room_leave_error",
                        "payload": {
                            "room_id": room_id,
                            "status": "error",
                            "message": "离开房间时发生错误"
                        }
                    })
            else:
                await websocket.send_json({
                    "type": "room_leave_error",
                    "payload": {
                        "status": "invalid",
                        "message": "缺少房间ID"
                    }
                })

        # elif message_type == "room_message":
        #     room_id = int(payload.get("room_id"))
        #     content = payload.get("content")
        #     if room_id:
        #         timestamp = datetime.now(timezone.utc).isoformat()
        #         ws_message = {
        #             "type": "room_message",
        #             "payload": {
        #                 "room_id": room_id,
        #                 "sender_id": user_id,
        #                 "content": content,
        #                 "timestamp": timestamp
        #             }
        #         }
        #         await manager.broadcast_to_room(room_id, ws_message, exclude_user=user_id)

        elif message_type == "set_vedio_url":
            room_id = int(payload.get("room_id"))
            url = payload.get("url")
            if room_id:
                timestamp = datetime.now(timezone.utc).isoformat()
                ws_message = {
                    "type": "set_vedio_url",
                    "payload": {
                        "room_id": room_id,
                        "sender_id": user_id,
                        "url": url,
                        "timestamp": timestamp
                    }
                }
                await manager.broadcast_to_room(room_id, ws_message, exclude_user=user_id)

        elif message_type == "set_vedio_start":
            room_id = int(payload.get("room_id"))
            if room_id:
                timestamp = datetime.now(timezone.utc).isoformat()
                ws_message = {
                    "type": "set_vedio_start",
                    "payload": {
                        "room_id": room_id,
                        "sender_id": user_id,
                        "timestamp": timestamp
                    }
                }
                await manager.broadcast_to_room(room_id, ws_message, exclude_user=user_id)

        elif message_type == "set_vedio_pause":
            room_id = int(payload.get("room_id"))
            if room_id:
                timestamp = datetime.now(timezone.utc).isoformat()
                ws_message = {
                    "type": "set_vedio_pause",
                    "payload": {
                        "room_id": room_id,
                        "sender_id": user_id,
                        "timestamp": timestamp
                    }
                }
                await manager.broadcast_to_room(room_id, ws_message, exclude_user=user_id)

                
        elif message_type == "set_vedio_jump":
            room_id = int(payload.get("room_id"))
            video_time_offset = payload.get("video_time_offset")
            timestamp = int(payload.get("timestamp"))
            if room_id:
                ws_message = {
                    "type": "set_vedio_jump",
                    "payload": {
                        "room_id": room_id,
                        "sender_id": user_id,
                        "video_time_offset": video_time_offset,
                        "timestamp": timestamp
                    }
                }
                await manager.broadcast_to_room(room_id, ws_message, exclude_user=user_id)

        else:
            # 未知消息类型
            logger.warning(f"Unknown message type '{message_type}' from user {user_id}")
            await websocket.send_json({
                "type": "error",
                "payload": {
                    "message": f"未知的消息类型: {message_type}",
                    "supported_types": ["ping", "enter_room", "leave_room"]
                }
            })
