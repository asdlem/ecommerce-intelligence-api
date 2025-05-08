"""测试路由

提供测试相关的API端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.dependencies.auth import get_current_user
from app.schemas.user import User
from app.schemas.token import LoginResponse, Token

router = APIRouter()

@router.get("/auth-test")
async def test_auth(current_user: User = Depends(get_current_user)):
    """
    测试认证依赖是否正常工作
    
    Args:
        current_user: 当前用户对象
        
    Returns:
        用户信息
    """
    return {
        "message": "认证成功",
        "user": current_user.dict(),
        "test_mode": True
    }

@router.get("/test-mode-check")
async def test_mode_check(request: Request):
    """
    检查请求是否在测试模式下
    
    Args:
        request: HTTP请求
        
    Returns:
        测试模式状态
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
    from app.core.config import settings
    if getattr(settings, "TEST_MODE", False):
        is_test_mode = True
    
    return {
        "is_test_mode": is_test_mode,
        "headers": {"X-Test-Mode": test_header},
        "query_params": {"test_mode": test_param},
        "env_config": {"TEST_MODE": getattr(settings, "TEST_MODE", False)}
    }

@router.post("/test-token", response_model=Token)
async def get_test_token():
    """
    获取测试令牌
    
    Returns:
        测试令牌
    """
    return {
        "access_token": "test_token_for_testing_purposes_only",
        "token_type": "bearer"
    } 