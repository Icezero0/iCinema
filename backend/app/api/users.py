from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from .. import crud, models, schemas
from ..database import get_db
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
import base64
import os
import random
import string

router = APIRouter()

# 密码加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 相关设置
SECRET_KEY = "c0da4f43a9a4a549d83a93a56f5d6e8257f5ed40218a9a8170705d6cfd8c9074"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await crud.users.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# 邮箱表单类
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
    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 创建访问令牌和刷新令牌
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/token/refresh")
async def refresh_token(
    refresh_token: str = Depends(OAuth2PasswordBearer(tokenUrl="token/refresh")),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
        
    user = await crud.users.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    # 创建新的访问令牌
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/users/", response_model=schemas.User)
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
    user.password = get_password_hash(user.password)
    return await crud.users.create_user(db=db, user=user)

@router.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(
    current_user: models.User = Depends(get_current_user)
):
    return current_user

@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    db_user = await crud.users.get_user_with_rooms(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/users/me", response_model=schemas.User)
async def update_user_me(
    email: str = Form(...),
    username: str = Form(None),
    avatar_base64: str = Form(None),
    password: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_data = {}
    if username is not None:
        db_user_by_username = await crud.users.get_user_by_username(db, username=username)
        if db_user_by_username is not None and getattr(db_user_by_username, "id", None) != current_user.id:
            raise HTTPException(status_code=400, detail="用户名已被使用！")
        update_data["username"] = username
    if avatar_base64 is not None:
        if avatar_base64.startswith('data:image/jpeg;base64,'):
            ext = 'jpg'
            avatar_data = avatar_base64.split('data:image/jpeg;base64,')[1]
        elif avatar_base64.startswith('data:image/png;base64,'):
            ext = 'png'
            avatar_data = avatar_base64.split('data:image/png;base64,')[1]
        elif avatar_base64.startswith('data:image/webp;base64,'):
            ext = 'webp'
            avatar_data = avatar_base64.split('data:image/webp;base64,')[1]
        else:
            raise HTTPException(status_code=400, detail="不支持的图片格式，仅支持jpg/png/webp")
        timestamp = int(datetime.now().timestamp())
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        # 文件名加上用户id作为标识
        filename = f"{timestamp}_uid{current_user.id}_{rand_str}.{ext}"
        avatar_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/upload/avatars'))
        os.makedirs(avatar_dir, exist_ok=True)
        file_path = os.path.join(avatar_dir, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(avatar_data))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"头像保存失败: {e}")
        icon_path = f"/avatars/{filename}"
        update_data["icon_path"] = icon_path
    if password is not None:
        hashed_password = get_password_hash(password)
        update_data["hashed_password"] = hashed_password
    db_user = await crud.users.get_user_by_email(db, email=email)
    if db_user is not None and getattr(db_user, "id", None) != current_user.id:
        raise HTTPException(status_code=400, detail="邮箱地址已被注册！")
    user_id = current_user.id
    if hasattr(user_id, 'original') or hasattr(user_id, 'expression'):
        user_id = getattr(current_user, '__dict__', {}).get('id', None)
    if not isinstance(user_id, int):
        raise HTTPException(status_code=500, detail="用户ID类型错误")
    return await crud.users.update_user(
        db=db,
        user_id=user_id,
        update_data=update_data
    )

@router.get("/token/check")
async def check_access_token(current_user: models.User = Depends(get_current_user)):
    return {"status": "valid"}
