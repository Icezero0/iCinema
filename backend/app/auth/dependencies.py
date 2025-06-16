"""
FastAPI认证依赖项
提供用于FastAPI路由的认证依赖项函数
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud
from ..schemas import User
from .config import TOKEN_URL
from .utils import verify_token

# OAuth2认证方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=TOKEN_URL)
refresh_token_scheme = OAuth2PasswordBearer(tokenUrl="token/refresh")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前认证用户 - FastAPI依赖项"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 验证token
    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception
    
    # 从数据库获取用户
    user = await crud.users.get_user(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """获取当前用户（可选） - 用于不强制要求认证的接口"""
    if token is None:
        return None
    
    user_id = verify_token(token)
    if user_id is None:
        return None
    
    user = await crud.users.get_user(db, user_id=user_id)
    return user
