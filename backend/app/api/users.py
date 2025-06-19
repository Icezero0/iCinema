from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from .. import crud, schemas
from ..database import get_db
from typing import List, Optional
from datetime import datetime
from app.auth import utils as auth_utils
from app.auth import dependencies as auth_deps
from app.auth.config import ACCESS_TOKEN_EXPIRE_MINUTES
import base64
import os
import random
import string

router = APIRouter()

# 登录用表单类
class OAuth2EmailRequestForm:
    def __init__(
        self,
        email: str = Form(...),
        password: str = Form(...)
    ):
        self.email = email
        self.password = password

@router.post("/token")
async def login(
    form_data: OAuth2EmailRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    user = await crud.users.get_user_by_email(db, form_data.email) 
    if not user or not auth_utils.verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 创建访问令牌和刷新令牌
    access_token = auth_utils.create_access_token(
        data={"sub": str(user.id)}
    )
    refresh_token = auth_utils.create_refresh_token(
        data={"sub": str(user.id)},
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/token/refresh")
async def refresh_token(
    refresh_token: str = Depends(auth_deps.refresh_token_scheme),
    db: AsyncSession = Depends(get_db)
):
    # 使用auth模块的verify_token函数
    uid = auth_utils.verify_token(refresh_token)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
        
    user = await crud.users.get_user(db, user_id=uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    # 创建新的访问令牌
    access_token = auth_utils.create_access_token(
        data={"sub": str(user.id)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/users", response_model=schemas.User)
async def create_user(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    # 检查邮箱是否已存在
    db_user = await crud.users.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="邮箱地址已被注册！"
        )
    # 检查用户名是否已存在
    db_user_by_username = await crud.users.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=400,
            detail="用户名已被使用！"
        )
    # 创建新用户，密码加密处理
    user.password = auth_utils.get_password_hash(user.password)
    return await crud.users.create_user(db=db, user=user)

@router.get("/users/me", response_model=schemas.UserDetailsResponse)
async def read_users_me(
    db: AsyncSession = Depends(get_db),
    include_room_details: bool = False,
    current_user = Depends(auth_deps.get_current_user)
):
    """
    获取当前登录用户的详细信息，包括基本信息、拥有的房间、加入的房间和通知
    
    参数:
    - rooms_skip: 房间分页起始位置
    - rooms_limit: 房间分页数量
    - notifications_skip: 通知分页起始位置
    - notifications_limit: 通知分页数量
    - include_room_details: 是否包含房间详细信息
    
    返回:
    - UserDetailsResponse: 包含用户基本信息、房间列表和通知列表的响应
    """
    if current_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    ROOMS_DEFAULT_LIMIT = 20

    # 获取用户拥有的房间
    owned_rooms, owned_total = await crud.rooms.get_owned_rooms(
        db=db,
        user_id=current_user.id,
        skip=0,
        limit=ROOMS_DEFAULT_LIMIT,
        include_details=include_room_details
    )
    
    # 获取用户加入的房间
    joined_rooms, joined_total = await crud.rooms.get_joined_rooms(
        db=db,
        user_id=current_user.id,
        skip=0,
        limit=ROOMS_DEFAULT_LIMIT,
        include_details=include_room_details
    )
    
    # 将ORM模型房间列表转换为Pydantic模型房间列表
    owned_rooms_schemas = [
        schemas.Room.model_validate(room, from_attributes=True) 
        for room in owned_rooms
    ]
    
    joined_rooms_schemas = [
        schemas.Room.model_validate(room, from_attributes=True) 
        for room in joined_rooms
    ]
    
    # 创建房间列表响应
    rooms_owned_response = schemas.RoomList(
        items=owned_rooms_schemas,
        total=owned_total
    )
    
    rooms_joined_response = schemas.RoomList(
        items=joined_rooms_schemas,
        total=joined_total
    )
    
    # 使用model_validate将ORM模型转换为Pydantic模型
    user_response = schemas.UserDetailsResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at,
        avatar_path=current_user.avatar_path,
        rooms_owned=rooms_owned_response,
        rooms_joined=rooms_joined_response
    )
    
    return user_response

@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    db_user: schemas.UserResponse = await crud.users.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/users/me", response_model=schemas.User)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user = Depends(auth_deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_data = {}

    # 获取当前用户ID
    user_id = current_user.id
    if not isinstance(user_id, int):
        raise HTTPException(status_code=500, detail="用户ID类型错误")
    
    # 检查邮箱是否匹配
    if user_update.email != current_user.email:
        raise HTTPException(status_code=400, detail="不能修改邮箱地址，请联系管理员！")

    # 检查新用户名是否已存在
    if user_update.username is not None:
        db_user_by_username = await crud.users.get_user_by_username(db, username=user_update.username)
        if db_user_by_username is not None and getattr(db_user_by_username, "id", None) != user_id:
            raise HTTPException(status_code=400, detail="用户名已被使用！")
        update_data["username"] = user_update.username
    
    # 解析并保存头像图片
    if user_update.avatar_base64 is not None:
        if user_update.avatar_base64.startswith('data:image/jpeg;base64,'):
            ext = 'jpg'
            avatar_data = user_update.avatar_base64.split('data:image/jpeg;base64,')[1]
        elif user_update.avatar_base64.startswith('data:image/png;base64,'):
            ext = 'png'
            avatar_data = user_update.avatar_base64.split('data:image/png;base64,')[1]
        elif user_update.avatar_base64.startswith('data:image/webp;base64,'):
            ext = 'webp'
            avatar_data = user_update.avatar_base64.split('data:image/webp;base64,')[1]
        else:
            raise HTTPException(status_code=400, detail="不支持的图片格式，仅支持jpg/png/webp")
        timestamp = int(datetime.now().timestamp())
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        filename = f"{timestamp}_uid{user_id}_{rand_str}.{ext}"
        avatar_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/upload/avatars'))
        os.makedirs(avatar_dir, exist_ok=True)
        file_path = os.path.join(avatar_dir, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(avatar_data))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"头像保存失败: {e}")
        avatar_path = f"/avatars/{filename}"
        update_data["avatar_path"] = avatar_path
    
    # 保存新密码
    if user_update.password is not None:
        hashed_password = auth_utils.get_password_hash(user_update.password)
        update_data["hashed_password"] = hashed_password
    
    return await crud.users.update_user(
        db=db,
        user_id=user_id,
        update_data=update_data
    )

@router.get("/token/check")
async def check_access_token(current_user = Depends(auth_deps.get_current_user)):
    return {"status": "valid"}

@router.get("/users", response_model=schemas.UserList)
async def list_users(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="分页起始位置"),
    limit: int = Query(20, ge=1, le=100, description="分页数量"),
    email: Optional[str] = Query(None, description="邮箱精确匹配"),
    username: Optional[str] = Query(None, description="用户名模糊匹配"),
    userid: Optional[int] = Query(None, description="用户ID精确匹配")
):
    """
    分页检索用户，支持邮箱、用户名、用户ID检索
    """
    # print(userid)
    users, total = await crud.users.get_users(db, skip=skip, limit=limit, email=email, username=username, userid=userid)
    user_items = [schemas.User.model_validate(user, from_attributes=True) for user in users]
    return schemas.UserList(items=user_items, total=total)
