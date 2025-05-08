from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.api.v1 import api_router
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware

# 设置日志
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加限流中间件
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 每分钟最大请求数
    window=60.0,       # 时间窗口（秒）
)

# 注册路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 异常处理
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后再试"},
    )

@app.get("/ping")
async def ping():
    """健康检查接口"""
    return {"status": "ok", "message": "服务正常运行"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 