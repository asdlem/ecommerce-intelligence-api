"""
Tables API - 数据表结构信息接口

此文件提供基本的数据表结构信息API，但不包含完整的查询功能实现。
所有高级查询功能应由data_query.py提供。此模块仅作为最小回退措施。
"""

from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import traceback

# 修正导入路径
from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.core.logging import get_logger
from app.core.config import settings
from app.db.session import get_db, engine
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

logger = get_logger(__name__)

router = APIRouter()

# 仅保留表获取功能，其他功能直接抛出异常
@router.get("/tables")
async def get_tables(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取数据库表列表
    
    返回系统中所有可查询的表名列表
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        表名列表
    """
    try:
        # 记录请求
        logger.info(f"用户 {current_user.username} 请求获取数据库表列表")
        
        # 实际查询数据库表结构
        # 这里使用SQLAlchemy内省获取表信息
        try:
            # 尝试获取数据库中的表
            from sqlalchemy import inspect
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            
            logger.info(f"成功从数据库获取表列表: {table_names}")
            
            # 返回实际的表列表
            return {
                "success": True,
                "data": table_names,
                "total": len(table_names)
            }
        except Exception as e:
            # 记录详细错误信息
            logger.error(f"从数据库获取表列表失败: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 直接抛出异常，不使用模拟数据
            raise HTTPException(
                status_code=500,
                detail=f"获取数据库表失败: {str(e)}"
            )
    
    except Exception as e:
        logger.error(f"获取数据库表列表失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"获取数据库表失败: {str(e)}"
        )

# 其他端点直接抛出异常，指示应使用data_query.py中的实现
@router.post("/nl2sql")
async def natural_language_to_sql(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    自然语言转SQL
    """
    logger.error("尝试使用tables.py中的nl2sql端点，但该模块不提供此功能")
    raise HTTPException(
        status_code=501,
        detail="此端点未实现。请使用data_query.py模块中的功能。模拟实现不可接受。"
    )

@router.post("/query")
async def execute_sql_query(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    执行SQL查询
    """
    logger.error("尝试使用tables.py中的query端点，但该模块不提供此功能")
    raise HTTPException(
        status_code=501,
        detail="此端点未实现。请使用data_query.py模块中的功能。模拟实现不可接受。"
    )

@router.post("/nl2sql-query")
async def data_query(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    执行自然语言数据查询
    """
    logger.error("尝试使用tables.py中的nl2sql-query端点，但该模块不提供此功能")
    raise HTTPException(
        status_code=501,
        detail="此端点未实现。请使用data_query.py模块中的功能。模拟实现不可接受。"
    )

@router.get("/history")
async def get_query_history(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取最近的查询历史
    """
    logger.error("尝试使用tables.py中的history端点，但该模块不提供此功能")
    raise HTTPException(
        status_code=501,
        detail="此端点未实现。请使用data_query.py模块中的功能。模拟实现不可接受。"
    ) 