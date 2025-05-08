"""认证相关路由

提供用户注册、登录、令牌刷新等认证相关功能。
"""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core import security
from app.core.config import settings
from app.db import crud
from app.db.session import get_db
from app.schemas.token import Token, LoginResponse
from app.schemas.user import User, UserCreate
from app.core.security import create_access_token
import logging

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    获取OAuth2兼容的令牌
    
    Args:
        db: 数据库会话
        form_data: 表单数据
        
    Returns:
        访问令牌
    """
    user = await crud.user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not await crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未激活"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User.model_validate(user)
    }


@router.post("/register", response_model=User)
async def register_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    注册新用户
    
    Args:
        db: 数据库会话
        user_in: 用户注册数据
        
    Returns:
        注册后的用户信息
    """
    try:
        # 记录请求参数，去除敏感信息
        logger.info(f"用户注册请求: username={user_in.username}, email={user_in.email}")
        
        # 检查用户名是否已存在
        user = await crud.user.get_by_username(db, username=user_in.username)
        if user:
            logger.warning(f"注册失败: 用户名 {user_in.username} 已被使用")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被使用"
            )
        
        # 检查邮箱是否已存在
        user = await crud.user.get_by_email(db, email=user_in.email)
        if user:
            logger.warning(f"注册失败: 邮箱 {user_in.email} 已被注册")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        logger.info(f"开始创建用户: {user_in.username}")
        
        # 在调试环境下，先记录用户数据结构
        logger.debug(f"注册数据: {user_in.model_dump()}")
        
        try:
            # 创建普通用户，简化参数
            user = await crud.user.create_user(
                db=db,
                obj_in={
                    "username": user_in.username,
                    "email": user_in.email,
                    "password": user_in.password
                }
            )
            
            logger.info(f"用户创建成功: {user.username} (ID: {user.id})")
        except Exception as create_error:
            # 详细记录创建用户的错误
            logger.error(f"创建用户失败: {str(create_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建用户失败: {str(create_error)}"
            )
        
        # 注释掉操作日志记录，因为operation_logs表不存在
        # try:
        #    await crud.operation_log.create(
        #        db=db,
        #        obj_in={
        #            "user_id": user.id,
        #            "operation_type": "register",
        #            "resource_type": "user",
        #            "resource_id": str(user.id),
        #            "details": {"username": user.username, "email": user.email},
        #            "status": "success"
        #        }
        #    )
        # except Exception as log_error:
        #    # 如果记录日志失败，仅记录错误但不影响用户注册
        #    logger.error(f"记录注册操作日志失败: {str(log_error)}")
        
        return user
    except HTTPException:
        # 直接重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录详细错误信息并返回详细错误给客户端（方便调试）
        logger.error(f"注册处理异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册处理异常: {str(e)}"
        )


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取当前用户信息
    """
    return current_user 