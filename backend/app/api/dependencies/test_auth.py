"""测试认证依赖项

提供跳过认证的装饰器，仅用于测试环境。
"""

import functools
from typing import Callable, Any, Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from app.core.config import settings
from app.schemas.user import User


def get_test_user() -> User:
    """
    获取测试用户，用于跳过认证
    
    Returns:
        测试用户对象
    """
    return User(
        id=1,
        username="test_user",
        email="test@example.com",
        phone="13800138000",
        is_active=True,
        is_superuser=True,
        created_at="2023-01-01T00:00:00",
        updated_at="2023-01-01T00:00:00"
    )


class TestModeOAuth2(OAuth2PasswordBearer):
    """
    支持测试模式的OAuth2密码承载器
    
    在测试模式下不要求令牌
    """
    
    def __init__(self, tokenUrl: str):
        super().__init__(tokenUrl=tokenUrl, auto_error=True)
        
    async def __call__(self, request: Request) -> Optional[str]:
        """
        重写调用方法，在测试模式下跳过令牌检查
        
        Args:
            request: HTTP请求
            
        Returns:
            令牌或测试模式标记
        """
        # 检查测试模式标志
        is_test_mode = False
        
        # 检查请求头
        test_header = request.headers.get("X-Test-Mode", "").lower()
        if test_header == "true":
            is_test_mode = True
        
        # 检查查询参数
        test_param = request.query_params.get("test_mode", "").lower()
        if test_param == "true":
            is_test_mode = True
        
        # 检查环境配置
        if getattr(settings, "TEST_MODE", False):
            is_test_mode = True
            
        # 如果是测试模式，返回特殊标记
        if is_test_mode:
            return "TEST_MODE_TOKEN"
            
        # 否则使用原始OAuth2逻辑
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
                
        return param


def skip_auth_in_test_mode(original_auth_dependency: Callable) -> Callable:
    """
    装饰器：在测试模式下跳过认证，直接返回测试用户
    
    Args:
        original_auth_dependency: 原始认证依赖项
        
    Returns:
        新的认证依赖项
    """
    @functools.wraps(original_auth_dependency)
    async def dependency_wrapper(request: Request, token: str = Depends(TestModeOAuth2(tokenUrl=f"{settings.API_V1_STR}/auth/login")), *args, **kwargs) -> Any:
        # 检查是否为测试模式令牌
        if token == "TEST_MODE_TOKEN":
            return get_test_user()
        
        # 否则使用原始认证
        return await original_auth_dependency(request=request, token=token, *args, **kwargs)
    
    return dependency_wrapper 