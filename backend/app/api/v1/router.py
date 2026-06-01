from fastapi import APIRouter

from app.api.v1 import auth, feedback, media, notifications, room_join_request, rooms, users, messages

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(rooms.router)
api_router.include_router(notifications.router)
api_router.include_router(room_join_request.router)
api_router.include_router(media.router)
api_router.include_router(messages.router)
api_router.include_router(feedback.router)
