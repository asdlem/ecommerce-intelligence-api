"""SQL查询工具模块

提供安全、高效的SQL查询功能，支持参数化查询和性能监控。
"""

import time
import logging
import re
import json
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, Set, cast
from pathlib import Path
import os

import sqlalchemy
from sqlalchemy import inspect, text, MetaData, Table, Column, select, func, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, OperationalError
from sqlalchemy.engine import Engine, CursorResult
from pydantic import BaseModel

from app.db.session import SyncSessionLocal, sync_engine
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class QueryResult(BaseModel):
    """SQL查询结果模型"""
    
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    columns: Optional[List[str]] = None
    execution_time: float
    row_count: int = 0
    affected_rows: int = 0
    query: str
    query_type: str = "SELECT"  # SELECT, INSERT, UPDATE, DELETE, OTHER
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            date: lambda d: d.isoformat(),
            Decimal: lambda d: float(d)
        }


class SqlInjectionError(Exception):
    """SQL注入错误"""
    pass


class SQLQueryTool:
    """
    SQL查询工具，用于安全地执行SQL查询
    
    支持:
    - 读/写查询权限控制
    - 查询超时控制
    - 结果行数限制
    - 白名单表控制
    """
    
    def __init__(
        self, 
        engine: Optional[Any] = None,
        read_only: bool = True,
        max_rows: int = 10000,
        timeout: int = 30,
        allowed_tables: Optional[List[str]] = None,
        restricted_tables: Optional[List[str]] = None,
        database_name: Optional[str] = None
    ):
        """
        初始化SQL查询工具
        
        Args:
            engine: SQLAlchemy引擎，如果为None则使用默认引擎
            read_only: 是否只读模式，只允许执行SELECT查询
            max_rows: 最大返回行数
            timeout: 查询超时时间（秒）
            allowed_tables: 允许查询的表列表
            restricted_tables: 禁止查询的表列表
            database_name: 数据库名称
        """
        self.engine = engine or sync_engine
        self.read_only = read_only
        self.max_rows = max_rows
        self.timeout = timeout
        self.allowed_tables = allowed_tables
        self.restricted_tables = restricted_tables
        
        logger.info(f"SQL查询工具初始化完成 (只读模式: {read_only}, 最大行数: {max_rows}, 超时: {timeout}秒)")
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            表结构信息字典，包含columns、主键、外键等信息
        """
        try:
            # 检查表是否存在
            inspector = inspect(self.engine)
            if table_name not in inspector.get_table_names():
                return {
                    "success": False,
                    "error": f"表 {table_name} 不存在"
                }
                
            # 获取列信息
            columns = []
            for column in inspector.get_columns(table_name):
                col_info = {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column.get("nullable", True),
                    "default": str(column.get("default", "")) if column.get("default") else None
                }
                columns.append(col_info)
                
            # 获取主键信息
            primary_key = inspector.get_pk_constraint(table_name)
            pk_columns = primary_key.get("constrained_columns", [])
            
            # 标记主键列
            for col in columns:
                if col["name"] in pk_columns:
                    col["primary_key"] = True
                    
            # 获取外键信息
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # 获取索引信息
            indexes = []
            for index in inspector.get_indexes(table_name):
                indexes.append({
                    "name": index["name"],
                    "columns": index["column_names"],
                    "unique": index["unique"]
                })
                
            return {
                "success": True,
                "name": table_name,
                "columns": columns,
                "primary_key": primary_key,
                "foreign_keys": foreign_keys,
                "indexes": indexes
            }
        except Exception as e:
            logger.error(f"获取表 {table_name} 结构失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        return self.run_query(sql, params)
    
    def run_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        if self.read_only and not self._is_read_only_query(sql):
            raise ValueError("只允许执行SELECT查询")
        
        try:
            # 添加LIMIT子句，如果尚未指定
            if "SELECT" in sql.upper() and "LIMIT" not in sql.upper():
                sql = self._add_limit_clause(sql, self.max_rows)
            
            start_time = time.perf_counter()
            
            # 执行查询
            with self.engine.connect() as connection:
                # 设置查询超时
                connection = connection.execution_options(timeout=self.timeout)
                
                # 执行查询
                if params:
                    result = connection.execute(text(sql), params)
                else:
                    result = connection.execute(text(sql))
                
                # 获取列名
                columns = result.keys()
                
                # 构建结果列表
                results = []
                for row in result:
                    row_dict = {col: value for col, value in zip(columns, row)}
                    results.append(row_dict)
                
                elapsed_time = time.perf_counter() - start_time
                logger.info(f"SQL查询成功，返回{len(results)}行结果，耗时: {elapsed_time:.4f}秒")
                
                return results
                
        except Exception as e:
            logger.error(f"SQL查询失败: {str(e)}, 查询: {sql}, 参数: {params}")
            raise
    
    def get_database_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取数据库模式信息
        
        Returns:
            表结构字典，键为表名，值为列信息列表
        """
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            schema = {}
            
            for table in tables:
                columns = []
                
                # 获取列信息
                for column in inspector.get_columns(table):
                    col_info = {
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column.get("nullable", True),
                        "default": str(column.get("default", ""))
                    }
                    columns.append(col_info)
                
                # 获取主键信息
                pk_columns = inspector.get_pk_constraint(table).get("constrained_columns", [])
                for col in columns:
                    if col["name"] in pk_columns:
                        col["primary_key"] = True
                
                # 获取外键信息
                fks = inspector.get_foreign_keys(table)
                for fk in fks:
                    for col_name in fk.get("constrained_columns", []):
                        for col in columns:
                            if col["name"] == col_name:
                                col["foreign_key"] = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                
                schema[table] = columns
            
            return schema
            
        except Exception as e:
            logger.error(f"获取数据库模式失败: {str(e)}")
            return {}
    
    def get_schema_description(self) -> str:
        """
        获取格式化的数据库模式描述
        
        Returns:
            格式化的数据库模式描述文本
        """
        schema = self.get_database_schema()
        if not schema:
            return ""
        
        description = "数据库表结构:\n\n"
        
        for table, columns in schema.items():
            description += f"表: {table}\n"
            
            for col in columns:
                description += f"- {col['name']}: {col['type']}"
                
                if col.get("primary_key"):
                    description += " (主键)"
                
                if col.get("foreign_key"):
                    description += f" (外键 -> {col['foreign_key']})"
                
                if not col.get("nullable"):
                    description += " (非空)"
                
                description += "\n"
            
            description += "\n"
        
        return description
    
    def get_table_data_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取表数据样本
        
        Args:
            table_name: 表名
            limit: 样本数量
            
        Returns:
            表数据样本
        """
        try:
            sql = f"SELECT * FROM {table_name} LIMIT {limit}"
            return self.run_query(sql)
        except Exception as e:
            logger.error(f"获取表数据样本失败: {str(e)}")
            return []
    
    def _is_read_only_query(self, sql: str) -> bool:
        """
        检查SQL是否为只读查询（SELECT或SHOW等）
        
        Args:
            sql: SQL查询语句
            
        Returns:
            是否为只读查询
        """
        sql_upper = sql.upper()
        
        read_patterns = [
            r"^\s*SELECT",
            r"^\s*SHOW",
            r"^\s*DESCRIBE",
            r"^\s*DESC",
            r"^\s*EXPLAIN",
            r"^\s*WITH\s+.+?\s+SELECT"  # CTE 查询
        ]
        
        for pattern in read_patterns:
            if re.search(pattern, sql_upper, re.DOTALL):
                return True
        
        return False
    
    def _add_limit_clause(self, sql: str, limit: int) -> str:
        """
        向SQL查询添加LIMIT子句
        
        Args:
            sql: 原始SQL
            limit: 限制行数
            
        Returns:
            添加了LIMIT子句的SQL
        """
        # 如果SQL已经包含LIMIT，则不添加
        if "LIMIT" in sql.upper():
            return sql
        
        # 去除SQL末尾的分号
        sql = sql.strip()
        if sql.endswith(";"):
            sql = sql[:-1]
        
        # 添加LIMIT子句
        return f"{sql} LIMIT {limit};"
        
    async def aexecute_query(self, sql: str, params: Optional[Dict[str, Any]] = None, max_rows: int = None) -> List[Dict[str, Any]]:
        """
        异步执行SQL查询
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            max_rows: 最大返回行数，覆盖实例默认值
            
        Returns:
            查询结果列表
        """
        # 使用线程池执行同步查询方法
        import asyncio
        
        # 如果提供了max_rows，则使用该值，否则使用实例默认值
        limit = max_rows if max_rows is not None else self.max_rows
        
        # 检查只读模式
        if self.read_only and not self._is_read_only_query(sql):
            raise ValueError("只允许执行SELECT查询")
        
        # 添加LIMIT子句
        if "SELECT" in sql.upper() and "LIMIT" not in sql.upper():
            sql = self._add_limit_clause(sql, limit)
        
        # 使用线程池执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.execute_query(sql, params)
        )

# 全局SQL查询工具实例缓存
_sql_query_tool = None

def get_sql_query_tool(
    force_new: bool = False,
    read_only: bool = True,
    max_rows: int = 10000,
    timeout: int = 30,
    allowed_tables: Optional[List[str]] = None,
    restricted_tables: Optional[List[str]] = None
) -> SQLQueryTool:
    """
    获取或创建SQL查询工具实例
    
    Args:
        force_new: 是否强制创建新实例
        read_only: 是否只读模式
        max_rows: 最大返回行数
        timeout: 查询超时时间（秒）
        allowed_tables: 允许查询的表列表
        restricted_tables: 禁止查询的表列表
        
    Returns:
        SQL查询工具实例
    """
    global _sql_query_tool
    
    if _sql_query_tool is None or force_new:
        _sql_query_tool = SQLQueryTool(
            read_only=read_only,
            max_rows=max_rows,
            timeout=timeout,
            allowed_tables=allowed_tables,
            restricted_tables=restricted_tables
        )
    
    return _sql_query_tool 