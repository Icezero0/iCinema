"""
JWT认证配置常量
统一管理所有认证相关的配置参数
"""

from datetime import timedelta

# JWT密钥和算法配置
SECRET_KEY = "c0da4f43a9a4a549d83a93a56f5d6e8257f5ed40218a9a8170705d6cfd8c9074"
ALGORITHM = "HS256"

# Token过期时间配置
ACCESS_TOKEN_EXPIRE_MINUTES = 180
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OAuth2配置
TOKEN_URL = "token"

# 密码加密配置
PWD_CONTEXT_SCHEMES = ["bcrypt"]
PWD_CONTEXT_DEPRECATED = "auto"
