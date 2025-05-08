"""请求限流中间件

提供基于内存的请求限流功能，保护API免受过度请求的影响。
"""

import time
from typing import Dict, Tuple, Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class RateLimiter:
    """内存中的请求计数器"""
    
    def __init__(self):
        self.requests: Dict[str, Tuple[int, float]] = {}
    
    def is_allowed(self, key: str, max_requests: int, window: float) -> bool:
        """
        检查请求是否被允许
        
        Args:
            key: 标识请求来源的键（通常是IP地址）
            max_requests: 时间窗口内允许的最大请求数
            window: 时间窗口（秒）
            
        Returns:
            是否允许请求
        """
        current_time = time.time()
        
        # 清理过期的记录
        self._clean_expired_records(current_time, window)
        
        # 如果键不存在，添加新记录并允许请求
        if key not in self.requests:
            self.requests[key] = (1, current_time)
            return True
        
        count, timestamp = self.requests[key]
        
        # 检查是否在时间窗口内超过最大请求数
        if current_time - timestamp <= window and count >= max_requests:
            return False
        
        # 如果在新窗口，重置计数器
        if current_time - timestamp > window:
            self.requests[key] = (1, current_time)
        else:
            # 更新计数器
            self.requests[key] = (count + 1, timestamp)
        
        return True
    
    def _clean_expired_records(self, current_time: float, window: float) -> None:
        """
        清理过期的记录
        
        Args:
            current_time: 当前时间戳
            window: 时间窗口（秒）
        """
        expired_keys = [
            key for key, (_, timestamp) in self.requests.items()
            if current_time - timestamp > window
        ]
        
        for key in expired_keys:
            del self.requests[key]


# 全局限流器实例
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """请求限流中间件"""
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window: float = 60.0,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        """
        初始化中间件
        
        Args:
            app: FastAPI应用
            max_requests: 时间窗口内允许的最大请求数
            window: 时间窗口（秒）
            key_func: 获取请求标识键的函数
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.key_func = key_func or self._default_key_func
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个请求处理函数
            
        Returns:
            响应对象
        """
        key = self.key_func(request)
        
        # 检查是否允许请求
        if not rate_limiter.is_allowed(key, self.max_requests, self.window):
            return Response(
                content="请求过于频繁，请稍后再试",
                status_code=HTTP_429_TOO_MANY_REQUESTS
            )
        
        # 处理请求
        return await call_next(request)
    
    def _default_key_func(self, request: Request) -> str:
        """
        默认的请求标识键函数，使用客户端IP
        
        Args:
            request: 请求对象
            
        Returns:
            请求标识键
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        client_host = request.client.host if request.client else "unknown"
        return client_host 
