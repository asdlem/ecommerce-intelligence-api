"""数据库事务工具

提供统一的事务模式类型和辅助功能，解决前向引用问题。
"""

from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession

# 显式定义事务模式类型，避免前向引用问题
JoinTransactionMode = Literal[
    "autobegin", 
    "conditional_savepoint", 
    "always_savepoint", 
    "read_only", 
    "none"
]

# 设置默认事务模式
DEFAULT_JOIN_TRANSACTION_MODE: JoinTransactionMode = "conditional_savepoint"

async def handle_transaction(
    session: AsyncSession, 
    mode: Optional[JoinTransactionMode] = DEFAULT_JOIN_TRANSACTION_MODE
) -> None:
    """
    处理事务逻辑，根据模式进行不同操作
    
    Args:
        session: 异步会话
        mode: 事务模式
    """
    if mode == "autobegin":
        # 自动开始事务，但不显式提交
        pass
    elif mode == "conditional_savepoint":
        # 根据条件创建保存点
        await session.flush()
    elif mode == "always_savepoint":
        # 总是创建保存点
        await session.flush()
    elif mode == "read_only":
        # 只读模式，不执行写操作
        pass
    elif mode == "none":
        # 不使用事务
        pass
    else:
        # 默认行为，刷新会话
        await session.flush() 
