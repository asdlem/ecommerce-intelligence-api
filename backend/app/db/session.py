from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 根据数据库类型设置不同的连接参数
common_params = {
    "echo": settings.DATABASE_ECHO,
    "pool_pre_ping": True,
}

mysql_params = {
    **common_params,
    "pool_recycle": 3600,
    "pool_size": 5,
    "max_overflow": 10,
}

sqlite_params = {
    **common_params,
}

# 创建异步引擎
if settings.DATABASE_TYPE == "sqlite":
    engine = create_async_engine(
        settings.DATABASE_URL,
        **sqlite_params
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        **mysql_params
    )

# 创建同步引擎（用于不支持异步的工具和脚本）
if settings.DATABASE_TYPE == "sqlite":
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite"),
        **sqlite_params
    )
else:
    # 使用PyMySQL作为MySQL连接器
    sync_url = settings.DATABASE_URL.replace("+aiomysql", "+pymysql")
    if "+pymysql" not in sync_url:
        # 如果URL中没有指定pymysql，添加它
        sync_url = sync_url.replace("mysql://", "mysql+pymysql://")
    sync_engine = create_engine(
        sync_url,
        **mysql_params
    )

# 创建异步会话工厂
async_session_factory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 创建同步会话工厂
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# 创建Base类，用于模型定义
Base = declarative_base()


# 异步会话上下文管理器
async def get_session() -> AsyncSession:
    """获取异步数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# 测试数据库连接
def test_connection():
    """测试数据库连接，返回是否连接成功"""
    try:
        with sync_engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("数据库连接成功")
            return True
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False

# 为了兼容代码，添加get_db作为get_session的别名
get_db = get_session 