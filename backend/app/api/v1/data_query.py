from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Request, Body
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, date
import asyncio
import json
from pydantic import BaseModel, Field
import traceback
import time

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.core.logging import get_logger
from app.db.session import get_db, AsyncSession
from app.core.config import settings

# 延迟导入查询代理，避免循环依赖
from app.services.ai.agents.query_agent import get_data_query_agent, stringify_special_objects
from app.services.ai.chains.nl2sql import get_nl2sql_chain
from app.utils.sql_query import get_sql_query_tool

logger = get_logger(__name__)

router = APIRouter()

# 为了使monkeypatch能工作，添加模块级引用
try:
    from app.services.ai.agents.query_agent import get_data_query_agent, stringify_special_objects
except ImportError:
    # 如果无法导入，创建一个占位函数
    def get_data_query_agent(*args, **kwargs):
        logger.warning("使用了占位get_data_query_agent函数，实际功能不可用")
        return None
    
    # 创建一个占位stringify_special_objects函数
    def stringify_special_objects(obj):
        if hasattr(obj, "content") and callable(getattr(obj, "content", None)):
            # 如果是AIMessage对象，提取其content
            return str(obj.content)
        elif hasattr(obj, "content") and isinstance(obj.content, str):
            # 如果有content属性且是字符串
            return str(obj.content)
        elif hasattr(obj, "__str__") and not isinstance(obj, (str, int, float, bool, list, dict, type(None))):
            # 如果是其他对象，转换为字符串
            return str(obj)
        elif isinstance(obj, dict):
            # 递归处理字典
            return {k: stringify_special_objects(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # 递归处理列表
            return [stringify_special_objects(item) for item in obj]
        else:
            # 保持原样
            return obj

# 缓存存储
query_cache = {}

# 查询请求模型
class DataQueryRequest(BaseModel):
    query: str = Field(..., description="自然语言查询")
    need_visualization: bool = Field(True, description="是否需要可视化")
    include_suggestions: bool = Field(True, description="是否包含查询建议")
    use_cache: bool = Field(False, description="是否使用缓存")
    
# 查询建议请求模型 - 已废弃，移除
# class QuerySuggestionRequest(BaseModel):
#    query: str = Field(..., description="当前查询")
#    results_summary: Optional[str] = Field(None, description="查询结果摘要")
    
# 查询建议响应模型 - 已废弃，移除
# class QuerySuggestionResponse(BaseModel):
#    suggestions: List[str] = Field(..., description="建议查询列表")

# 简单的内存缓存，可以根据需要替换为Redis等分布式缓存
QUERY_CACHE = {}
CACHE_TTL = timedelta(minutes=30)  # 默认缓存30分钟

def _is_cache_valid(key: str) -> bool:
    """检查缓存是否有效"""
    if key not in QUERY_CACHE:
        return False
    
    cache_time = QUERY_CACHE[key]["timestamp"]
    now = datetime.now()
    
    # 如果缓存时间超过TTL，则认为缓存无效
    return (now - cache_time) < CACHE_TTL

def _clean_expired_cache():
    """清理过期缓存"""
    now = datetime.now()
    expired_keys = []
    
    for key, cache_data in QUERY_CACHE.items():
        if (now - cache_data["timestamp"]) > CACHE_TTL:
            expired_keys.append(key)
    
    for key in expired_keys:
        del QUERY_CACHE[key]
    
    logger.info(f"已清理 {len(expired_keys)} 条过期缓存")

@router.post("/nl2sql-query")
async def data_query(
    request: DataQueryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    执行自然语言数据查询
    
    接收自然语言查询，将其转换为SQL，执行查询并返回结果。
    可以选择是否包含可视化配置和后续查询建议。
    
    Args:
        request: 查询请求
        background_tasks: 后台任务
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        查询结果及相关信息
    """
    start_time = datetime.now()
    try:
        query = request.query.strip()
        logger.info(f"用户({current_user.id})执行数据查询: {query}")
        
        # 获取nl2sql链对象
        nl2sql_chain = get_nl2sql_chain()
        
        # 生成SQL和建议
        logger.debug(f"开始生成SQL: {query}")
        sql, suggestions = await nl2sql_chain.generate_sql_with_suggestions(query)
        logger.info(f"SQL生成结果: {sql[:100]}...")
    
        # 检查SQL生成是否成功
        if not sql or sql.startswith("__ERROR__"):
            error_message = sql.replace("__ERROR__:", "").strip() if sql else "SQL生成失败"
            logger.warning(f"SQL生成失败: {error_message}")
            
            # 记录失败的查询
            from app.db.crud import ai_query_log
            processing_time = (datetime.now() - start_time).total_seconds()
            await ai_query_log.create_log(
                db=db,
                user_id=current_user.id,
                query_type="nl2sql",
                query_text=query,
                model_used=getattr(nl2sql_chain, "model_name", None),
                status="error",
                response_text=error_message,
                processing_time=processing_time,
                meta_info={
                    "error": error_message,
                    "suggestions": suggestions
                }
            )
            
            return {
                "success": False,
                "data": {
                    "error": error_message,
                    "message": "SQL生成失败，请重新描述您的查询",
                    "suggestions": suggestions  # 仍然返回建议
                },
                "total": 0
            }
        
        # 执行查询
        logger.debug(f"开始执行SQL查询: {sql}")
        results, row_count = await nl2sql_chain.execute_query(sql)
        logger.info(f"SQL查询执行完成，返回{row_count}条结果")
    
        # 生成结果解释（如果有结果）
        explanation = ""
        """
        if results:
            try:
                logger.debug("开始生成结果解释")
                explanation = await nl2sql_chain.explain_results(query, sql, results)
                logger.debug(f"解释生成完成: {explanation[:100]}...")
            except Exception as e:
                logger.error(f"生成结果解释失败: {str(e)}")
                explanation = "无法生成解释。"
        """
        
        # 生成可视化配置（如果需要）
        visualization_config = {}
        if request.need_visualization and results:
            try:
                logger.debug("开始生成可视化配置")
                visualization_config = await nl2sql_chain.generate_visualization_config(
                    query, sql, results
                )
                logger.debug("可视化配置生成完成")
            except Exception as e:
                logger.error(f"生成可视化配置失败: {str(e)}")
        
        # 整合结果
        result = {
            "query": query,
            "sql": sql,
            "results": results,
            "row_count": row_count,
            "explanation": explanation,
            "visualization": visualization_config if request.need_visualization else None,
            "suggestions": suggestions  # 包含生成的建议
        }
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 记录查询结果到数据库
        async def log_query_to_db(query_result, user_id, db_session, processing_time):
            try:
                from app.db.crud import ai_query_log
                
                # 提取必要的信息
                sql = query_result.get("sql", "")
                row_count = query_result.get("row_count", 0)
                
                # 避免存储过大的结果
                response_summary = f"返回{row_count}条记录。" + (query_result.get("explanation", "")[:500] if query_result.get("explanation") else "")
                
                await ai_query_log.create_log(
                    db=db_session,
                    user_id=user_id,
                    query_type="nl2sql",
                    query_text=query,
                    model_used=getattr(nl2sql_chain, "model_name", None),
                    status="success",
                    response_text=response_summary,
                    processing_time=processing_time,
                    meta_info={
                        "sql": sql,
                        "row_count": row_count,
                        "has_visualization": bool(visualization_config),
                        "suggestions_count": len(suggestions) if suggestions else 0
                    }
                )
                logger.info(f"成功记录用户({user_id})的查询到数据库")
            except Exception as e:
                logger.error(f"记录查询到数据库失败: {str(e)}", exc_info=True)
                
        # 添加后台任务来记录查询
        background_tasks.add_task(log_query_to_db, result, current_user.id, db, processing_time)
        
        logger.info(f"查询完成，处理时间: {processing_time:.2f}秒")
        
        # 返回结果
        return {
            "success": True,
            "data": result,
            "total": result.get("row_count", 0) if isinstance(result, dict) else 0
        }
    except Exception as e:
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.error(f"执行数据查询失败: {str(e)}", exc_info=True)
        
        # 记录失败的查询
        try:
            from app.db.crud import ai_query_log
            await ai_query_log.create_log(
                db=db,
                user_id=current_user.id,
                query_type="nl2sql",
                query_text=request.query.strip(),
                status="error",
                response_text=str(e),
                processing_time=processing_time,
                meta_info={"error": str(e)}
            )
        except Exception as log_error:
            logger.error(f"记录失败查询到数据库时出错: {str(log_error)}")
        
        return {
            "success": False,
            "data": {
                "error": str(e),
                "message": "查询执行失败，请重试"
            },
            "total": 0
        }

@router.get("/history")
async def get_query_history(
    limit: int = 10,
    offset: int = 0,
    query_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取最近的查询历史
    
    从数据库中获取用户的查询历史记录
    
    Args:
        limit: 返回的记录数量
        offset: 分页偏移量
        query_type: 查询类型过滤
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        查询历史列表
    """
    try:
        logger.info(f"获取用户({current_user.id})的查询历史，limit={limit}, offset={offset}, type={query_type}")
        
        from app.db.crud import ai_query_log
        
        # 从数据库中获取查询历史
        history_records = await ai_query_log.get_user_query_history(
            db=db,
            user_id=current_user.id,
            query_type=query_type,
            limit=limit,
            offset=offset
        )
        
        # 格式化返回数据
        formatted_records = []
        for record in history_records:
            formatted_records.append({
                "id": record.id,
                "query": record.query_text,
                "query_type": record.query_type,
                "timestamp": record.created_at,
                "status": record.status,
                "model": record.model_used,
                "processing_time": record.processing_time
            })
        
        logger.info(f"成功获取查询历史，返回{len(formatted_records)}条记录")
        
        # 使用测试脚本期望的历史记录格式返回
        return {
            "history": formatted_records
        }
    except Exception as e:
        logger.error(f"获取查询历史失败: {str(e)}", exc_info=True)
        return {
            "history": [],
            "error": str(e)
        }

@router.delete("/cache")
async def clear_query_cache(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    清除查询缓存
    
    清空所有缓存的查询结果
    
    Args:
        current_user: 当前用户
        
    Returns:
        清除结果
    """
    try:
        # 记录清除的缓存数量
        cache_count = len(QUERY_CACHE)
        QUERY_CACHE.clear()
        
        logger.info(f"已清除所有查询缓存，共 {cache_count} 条")
        
        return {
            "success": True,
            "message": "已清除所有查询缓存",
            "count": cache_count
        }
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "清除缓存失败"
        }

# NL2SQL请求模型
class NL2SQLRequest(BaseModel):
    query: str = Field(..., description="自然语言查询")

# NL2SQL响应模型
class NL2SQLResponse(BaseModel):
    sql: str = Field(..., description="生成的SQL查询")
    success: bool = Field(..., description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    suggestions: Optional[List[str]] = Field(None, description="查询建议列表")

@router.post("/nl2sql", response_model=NL2SQLResponse)
async def natural_language_to_sql(
    request: NL2SQLRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    自然语言转SQL
    
    将自然语言查询转换为SQL语句，不执行查询
    
    Args:
        request: 请求体
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        SQL语句和建议
    """
    start_time = datetime.now()
    
    try:
        query = request.query.strip()
        logger.info(f"用户({current_user.id})执行NL2SQL转换: {query}")
        
        # 获取nl2sql链对象
        nl2sql_chain = get_nl2sql_chain()
        
        # 生成SQL和建议
        logger.debug(f"开始生成SQL: {query}")
        sql, suggestions = await nl2sql_chain.generate_sql_with_suggestions(query)
        logger.info(f"SQL生成结果: {sql[:100]}...")
        
        # 检查SQL生成是否成功
        if not sql or sql.startswith("__ERROR__"):
            error_message = sql.replace("__ERROR__:", "").strip() if sql else "SQL生成失败"
            logger.warning(f"SQL生成失败: {error_message}")
            
            # 记录失败的查询
            processing_time = (datetime.now() - start_time).total_seconds()
            from app.db.crud import ai_query_log
            await ai_query_log.create_log(
                db=db,
                user_id=current_user.id,
                query_type="nl2sql-only",
                query_text=query,
                model_used=getattr(nl2sql_chain, "model_name", None),
                status="error",
                response_text=error_message,
                processing_time=processing_time,
                meta_info={
                    "error": error_message,
                    "suggestions": suggestions
                }
            )
            
            return {
                "sql": "",
                "success": False,
                "error": error_message,
                "suggestions": suggestions
            }
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 记录成功查询
        from app.db.crud import ai_query_log
        await ai_query_log.create_log(
            db=db,
            user_id=current_user.id,
            query_type="nl2sql-only",
            query_text=query,
            model_used=getattr(nl2sql_chain, "model_name", None),
            status="success",
            response_text=sql,
            processing_time=processing_time,
            meta_info={
                "sql": sql,
                "suggestions_count": len(suggestions) if suggestions else 0
            }
        )
        
        logger.info(f"NL2SQL转换完成，处理时间: {processing_time:.2f}秒")
        
        return {
            "sql": sql,
            "success": True,
            "error": None,
            "suggestions": suggestions
        }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"NL2SQL转换失败: {str(e)}", exc_info=True)
        
        # 记录失败的查询
        try:
            from app.db.crud import ai_query_log
            await ai_query_log.create_log(
                db=db,
                user_id=current_user.id,
                query_type="nl2sql-only",
                query_text=request.query.strip(),
                status="error",
                response_text=str(e),
                processing_time=processing_time,
                meta_info={"error": str(e)}
            )
        except Exception as log_error:
            logger.error(f"记录失败查询到数据库时出错: {str(log_error)}")
        
        return {
            "sql": "",
            "success": False,
            "error": str(e),
            "suggestions": None
        }

class SQLQueryRequest(BaseModel):
    query: str = Field(..., description="SQL查询语句")
    max_rows: int = Field(1000, description="最大返回行数")

@router.get("/tables")
async def get_tables(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取数据库中所有表的列表
    
    返回数据库中所有可用表的列表。
    
    Args:
        current_user: 当前用户
        
    Returns:
        表名列表
    """
    try:
        # 获取SQL查询工具
        sql_tool = get_sql_query_tool(read_only=True)
        
        # 获取数据库表
        query = "SHOW TABLES"
        results = sql_tool.execute_query(query)
        
        # 提取表名
        table_list = []
        for row in results:
            # 提取第一个值（表名）添加到列表
            table_list.append(list(row.values())[0])
        
        # 统一返回格式，使用data字段包装数据
        return {
            "success": True,
            "data": table_list,
            "total": len(table_list)
        }
    
    except Exception as e:
        logger.error(f"获取数据库表列表失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"获取数据库表列表失败: {str(e)}",
            "data": []
        }

@router.post("/query")
async def execute_sql_query(
    request: SQLQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    执行SQL查询
    
    直接执行提供的SQL查询语句，返回结果
    
    Args:
        request: SQL查询请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        查询结果
    """
    start_time = datetime.now()
    
    try:
        # 获取查询工具
        query_tool = get_sql_query_tool()
        
        # 添加日志记录
        sql = request.query.strip()
        logger.info(f"用户({current_user.id})执行SQL查询: {sql[:200]}...")
        
        # 执行查询
        logger.debug(f"开始执行SQL查询")
        results, row_count = await query_tool.execute_query(
            sql, 
            max_rows=request.max_rows
        )
        
        # 记录执行结果
        logger.info(f"SQL查询执行完成，返回{row_count}条结果")
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 记录查询到数据库
        from app.db.crud import ai_query_log
        await ai_query_log.create_log(
            db=db,
            user_id=current_user.id,
            query_type="sql-direct",
            query_text=sql,
            status="success",
            response_text=f"返回{row_count}条结果",
            processing_time=processing_time,
            meta_info={
                "sql": sql,
                "row_count": row_count,
                "max_rows": request.max_rows
            }
        )
        
        # 返回结果
        return {
            "success": True,
            "data": {
                "results": results,
                "row_count": row_count,
                "query": sql,
                "execution_time": processing_time
            },
            "total": row_count
        }
    except Exception as e:
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.error(f"执行SQL查询失败: {str(e)}", exc_info=True)
        
        # 记录失败的查询
        try:
            from app.db.crud import ai_query_log
            await ai_query_log.create_log(
                db=db,
                user_id=current_user.id,
                query_type="sql-direct",
                query_text=request.query.strip(),
                status="error",
                response_text=str(e),
                processing_time=processing_time,
                meta_info={"error": str(e)}
            )
        except Exception as log_error:
            logger.error(f"记录失败查询到数据库时出错: {str(log_error)}")
        
        return {
            "success": False,
            "error": str(e),
            "data": {
                "message": "查询执行失败，请检查SQL语法或数据库连接"
            },
            "total": 0
        }

# 解释请求模型
class ExplainResultsRequest(BaseModel):
    query: str = Field(..., description="用户原始查询")
    sql: str = Field(..., description="SQL查询语句")
    results: List[Dict[str, Any]] = Field(..., description="查询结果")

@router.post("/explain-results")
async def explain_query_results(
    request: ExplainResultsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    生成查询结果的解释
    
    接收查询、SQL和结果，生成自然语言解释
    
    Args:
        request: 解释请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        解释内容
    """
    start_time = datetime.now()
    try:
        query = request.query.strip()
        sql = request.sql.strip()
        results = request.results
        
        logger.info(f"用户({current_user.id})请求生成解释: {query}")
        
        # 获取nl2sql链对象
        nl2sql_chain = get_nl2sql_chain()
        
        # 生成解释
        logger.debug(f"开始生成解释")
        explanation = await nl2sql_chain.explain_results(query, sql, results)
        logger.info(f"解释生成完成: {explanation[:100]}...")
        
        # 记录到日志
        processing_time = (datetime.now() - start_time).total_seconds()
        from app.db.crud import ai_query_log
        await ai_query_log.create_log(
            db=db,
            user_id=current_user.id,
            query_type="explain",
            query_text=query,
            model_used=getattr(nl2sql_chain, "model_name", None),
            status="success",
            response_text=explanation,
            processing_time=processing_time,
            meta_info={
                "sql": sql,
                "results_count": len(results) if results else 0
            }
        )
        
        return {
            "success": True,
            "data": {
                "explanation": explanation
            }
        }
        
    except Exception as e:
        logger.error(f"生成解释失败: {str(e)}")
        
        error_detail = str(e)
        if "traceback" not in error_detail:
            # 捕获并记录详细堆栈信息，但不发送给客户端
            tb = traceback.format_exc()
            logger.error(f"解释生成异常堆栈: {tb}")
        
        # 记录失败日志
        try:
            processing_time = (datetime.now() - start_time).total_seconds()
            from app.db.crud import ai_query_log
            await ai_query_log.create_log(
                db=db,
                user_id=current_user.id,
                query_type="explain",
                query_text=request.query,
                status="error",
                response_text=error_detail,
                processing_time=processing_time
            )
        except Exception as log_err:
            logger.error(f"记录解释失败日志出错: {str(log_err)}")
        
        return {
            "success": False,
            "message": f"生成解释失败: {error_detail}"
        } 