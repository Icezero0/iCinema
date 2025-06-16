"""
认证相关的Pydantic模式
定义认证请求和响应的数据结构
"""

from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    """Token响应模式"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Token数据模式"""
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    """登录请求模式"""
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    """刷新Token请求模式"""
    refresh_token: str
