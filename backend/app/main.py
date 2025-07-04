from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .api import users, rooms, notifications, messages
from .websocket import routes as websocket_routes
from contextlib import asynccontextmanager
from app.database import engine
from app.models import Base

import logging
import os

logging.basicConfig(level=logging.INFO)

# 创建上传目录存在
avatars_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/upload/avatars'))
os.makedirs(avatars_dir, exist_ok=True)

# 生命周期配置
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    

app = FastAPI(lifespan=lifespan)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 静态文件服务
# app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/avatars", StaticFiles(directory="../data/upload/avatars"), name="avatars")

# 包含路由
app.include_router(users.router, tags=["users"])
app.include_router(rooms.router, tags=["rooms"])
app.include_router(notifications.router, tags=["notifications"])
app.include_router(messages.router, tags=["messages"])
app.include_router(websocket_routes.router, tags=["websocket"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to iCinema API"}