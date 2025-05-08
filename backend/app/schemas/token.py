"""令牌相关模型

包含JWT令牌相关的Pydantic模型。
"""

from typing import Optional
from pydantic import BaseModel

from app.schemas.user import User


class Token(BaseModel):
    """访问令牌模型"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """令牌载荷模型"""
    sub: Optional[str] = None
    exp: Optional[int] = None


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str
    user: User 