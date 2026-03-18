from fastapi import APIRouter

from app.api.v1 import auth, notifications, rooms, users, room_join_request

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(rooms.router)
api_router.include_router(notifications.router)
api_router.include_router(room_join_request.router)