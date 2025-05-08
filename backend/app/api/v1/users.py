"""
用户管理API模块

提供用户信息查询、个人资料管理等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, List, Optional
from pydantic import BaseModel

from app.db.session import get_db, AsyncSession
from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

class UserInfo(BaseModel):
    """用户信息响应模型"""
    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool
    status: str
    
@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取当前用户信息
    
    返回当前已登录用户的详细信息
    """
    logger.info(f"用户({current_user.id})请求个人信息")
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "status": current_user.status
    }

# 暂时只实现获取当前用户信息的接口
# 其他接口如用户列表、用户详情、修改用户等将在后续开发中添加 