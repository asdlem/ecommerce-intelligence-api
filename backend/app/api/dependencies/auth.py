"""认证依赖项

提供FastAPI的依赖项，用于API路由的认证和权限检查。
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status, Query, Request
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.core.security import ALGORITHM
from app.core.config import settings
from app.db.session import get_db
from app.db import crud
from app.db.transaction import JoinTransactionMode, DEFAULT_JOIN_TRANSACTION_MODE
from app.schemas.token import TokenPayload
from app.schemas.user import User
from app.db.models import Role

# 导入测试模式装饰器和自定义OAuth2方案
from app.api.dependencies.test_auth import TestModeOAuth2, get_test_user

# 创建自定义OAuth2方案
oauth2_scheme = TestModeOAuth2(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# 认证依赖
async def get_current_user(
    request: Request = None,
    db: AsyncSession = Depends(get_db), 
    token: str = Depends(oauth2_scheme),
    transaction_mode: JoinTransactionMode = Query(DEFAULT_JOIN_TRANSACTION_MODE)
) -> User:
    """
    获取当前用户
    
    Args:
        request: HTTP请求
        db: 数据库会话
        token: JWT令牌
        transaction_mode: 事务模式
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 认证错误
    """
    try:
        # 测试模式令牌验证
        if token == "TEST_MODE_TOKEN":
            # 测试模式下返回测试用户
            return get_test_user()

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[ALGORITHM]
            )
            token_data = TokenPayload(**payload)
        except Exception as e:
            print(f"JWT解码错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无法验证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 打印Token信息用于调试
        print(f"Token Subject: {token_data.sub}")
        
        # 检查是否应该使用测试用户
        if token_data.sub == str(settings.TEST_USER_ID):
            print("使用测试用户 (通过JWT)")
            return get_test_user()
        
        # 从数据库获取用户
        user = await crud.user.get(db, id=int(token_data.sub))
        
        # 打印用户信息用于调试
        print(f"User found: {user is not None}")
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户未找到"
            )
        
        if not await crud.user.is_active(user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="用户未激活"
            )
        
        return user
        
    except Exception as e:
        print(f"认证过程中发生未处理异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误，请稍后再试"
        )


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前用户的超级用户权限
    
    Args:
        current_user: 当前用户对象
        
    Returns:
        超级用户对象
        
    Raises:
        HTTPException: 权限错误
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="没有权限访问"
        )
    
    return current_user


# 为了兼容代码，添加别名
get_current_admin_user = get_current_active_superuser


async def check_permissions(
    required_permissions: List[str], user_id: int, db: AsyncSession
) -> bool:
    """
    检查用户是否具有给定的权限
    
    Args:
        required_permissions: 需要的权限列表
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        是否具有权限
    """
    # 获取用户角色列表
    user_roles_query = await db.execute(
        "SELECT role_id FROM user_roles WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    user_role_ids = [row[0] for row in user_roles_query.fetchall()]
    
    # 获取角色权限列表
    for role_id in user_role_ids:
        role = await crud.role.get(db=db, id=role_id)
        if role and role.permissions:
            role_permissions = role.permissions.get("permissions", [])
            # 检查是否具有所有需要的权限
            if all(perm in role_permissions for perm in required_permissions):
                return True
    
    return False


def require_permissions(required_permissions: List[str]):
    """
    创建一个权限检查函数
    
    Args:
        required_permissions: 需要的权限列表
        
    Returns:
        权限检查函数
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # 检查当前用户是否为超级用户
        if current_user.is_superuser:
            return True
            
        has_permission = await check_permissions(
            required_permissions, current_user.id, db
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问"
            )
        
        return True
    
    return permission_checker 
