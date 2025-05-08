#!/usr/bin/env python
"""
查询Agent - 数据查询和分析
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
import random
import re
from uuid import uuid4

from app.core.logging import get_logger
from app.core.config import settings
from app.services.ai.chains.nl2sql import NL2SQLChain
from app.services.ai.adapters.langchain_llm import LangChainAdapter, extract_content_from_response
from app.services.ai.memory import ConversationMemory

# 日志配置
logger = get_logger(__name__)

# 缓存AI代理实例
_data_query_agent = None

def get_data_query_agent(force_new: bool = False):
    """
    获取或创建数据查询代理实例
    
    Args:
        force_new: 是否强制创建新实例
    
    Returns:
        数据查询代理实例
    """
    global _data_query_agent
    
    if _data_query_agent is None or force_new:
        _data_query_agent = DataQueryAgent()
        
    return _data_query_agent

def stringify_special_objects(data):
    """
    递归将不可JSON序列化的对象转换为字符串
    
    Args:
        data: 要序列化的数据
        
    Returns:
        处理后的数据
    """
    if data is None:
        return None
        
    if isinstance(data, (str, int, float, bool)):
        return data
        
    if isinstance(data, (datetime,)):
        return data.isoformat()
        
    if hasattr(data, 'content') and isinstance(data.content, str):
        # 处理LangChain消息对象
        return data.content
        
    if hasattr(data, 'model_dump'):
        # 处理Pydantic模型
        try:
            return data.model_dump()
        except:
            return str(data)
            
    if hasattr(data, 'dict') and callable(data.dict):
        # 处理旧版Pydantic模型
        try:
            return data.dict()
        except:
            return str(data)
            
    if hasattr(data, 'to_dict') and callable(data.to_dict):
        # 处理某些ORM模型
        try:
            return data.to_dict()
        except:
            return str(data)
            
    if isinstance(data, dict):
        return {k: stringify_special_objects(v) for k, v in data.items()}
        
    if isinstance(data, (list, tuple)):
        return [stringify_special_objects(item) for item in data]
        
    # 默认转换为字符串
    try:
        return str(data)
    except:
        return "无法序列化的对象"

"""查询Agent模块

协调各组件处理自然语言查询、数据库查询和可视化。
"""

import logging
import json
from typing import Any, Dict, List, Optional, Union, Tuple
import asyncio
from datetime import datetime
from uuid import uuid4

# 我们将直接导入这些依赖，而不是延迟导入
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.logging import get_logger
from app.services.ai.adapters.langchain_llm import LangChainAdapter, extract_content_from_response
from app.services.ai.chains.nl2sql import NL2SQLChain, get_nl2sql_chain, DatabaseToolkit
from app.services.ai.memory import ConversationMemory

logger = get_logger(__name__)


class DataQueryAgent:
    """数据查询Agent类，协调各组件处理自然语言查询"""
    
    def __init__(self):
        """
        初始化数据查询Agent
        """
        self.llm_adapter = LangChainAdapter(temperature=0.1)
        self.memory = ConversationMemory(window_size=5)  # 保留最近5轮对话
        
        # 初始化NL2SQL链
        try:
            # 初始化NL2SQL链，使用配置参数传递设置
            self.nl2sql_chain = NL2SQLChain(
                config={
                    "need_explanation": True,
                    "need_visualization": True,
                    "need_suggestions": True
                }
            )
            logger.info("数据查询代理初始化完成")
        except Exception as e:
            logger.error(f"NL2SQL链初始化错误: {str(e)}")
            # 即使初始化失败，也创建一个实例以避免空引用
            self.nl2sql_chain = NL2SQLChain()
    
    async def analyze_query_intent(self, query: str) -> Dict:
        """
        分析查询意图
        
        Args:
            query: 用户查询
            
        Returns:
            查询意图分析结果
        """
        try:
            # 构建意图分析提示词
            prompt = f"""分析以下数据查询的意图，确定用户想要了解的信息：

查询: {query}

请提供以下信息:
1. 查询主题 (例如: 销售额, 客户行为, 库存等)
2. 查询目标 (例如: 排名前10, 同比增长, 分布情况等)
3. 时间范围 (例如: 过去30天, 上个月, 2023年全年等)
4. 可能相关的数据维度 (例如: 产品类别, 地区, 客户类型等)

以JSON格式返回，包含上述字段。
"""
            
            # 调用LLM分析意图
            response = await self.llm_adapter.generate(prompt=prompt, max_tokens=500)
            
            # 尝试解析返回的JSON
            intent_str = extract_content_from_response(response)
            
            # 尝试提取JSON
            import re
            import json
            json_match = re.search(r'\{.*\}', intent_str, re.DOTALL)
            if json_match:
                try:
                    intent_json = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.warning(f"无法解析JSON: {json_match.group(0)}")
                    intent_json = {
                        "query_topic": "未识别",
                        "query_goal": "未识别",
                        "time_range": "未指定",
                        "dimensions": []
                    }
            else:
                # 如果没有找到JSON格式，则创建基本结构
                intent_json = {
                    "query_topic": "未识别",
                    "query_goal": "未识别",
                    "time_range": "未指定",
                    "dimensions": []
                }
            
            return intent_json
            
        except Exception as e:
            logger.error(f"分析查询意图失败: {str(e)}")
            # 返回默认结构
            return {
                "query_topic": "未识别",
                "query_goal": "未识别",
                "time_range": "未指定",
                "dimensions": []
            }
    
    async def query(self, query: str, need_visualization: bool = True, include_suggestions: bool = True) -> Dict:
        """
        执行查询
        
        Args:
            query: 自然语言查询
            need_visualization: 是否需要可视化配置
            include_suggestions: 是否包含后续查询建议
            
        Returns:
            查询结果
        """
        try:
            # 1. 分析查询意图
            intent = await self.analyze_query_intent(query)
            logger.debug(f"查询意图分析: {json.dumps(intent, ensure_ascii=False)}")
            
            # 2. 生成SQL
            sql = await self.nl2sql_chain.generate_sql(query)
            logger.info(f"生成的SQL: {sql}")
            
            # 3. 执行SQL查询
            results, row_count = await self.nl2sql_chain.execute_query(sql)
            
            # 记录结果
            if results:
                logger.info(f"查询成功, 返回{row_count}行结果")
                if row_count > 0:
                    logger.debug(f"结果样例: {json.dumps(results[0], ensure_ascii=False)}")
            else:
                logger.warning("查询未返回结果")
                
            # 4. 生成结果解释
            explanation = await self.nl2sql_chain.explain_results(query, sql, results)
            
            # 5. 生成可视化配置(如需要)
            visualization_config = None
            if need_visualization and results:
                visualization_config = await self.nl2sql_chain.generate_visualization_config(query, sql, results)
                
            # 6. 生成后续查询建议(如需要)
            query_suggestions = []
            if include_suggestions:
                query_suggestions = await self.nl2sql_chain.suggest_queries(query, sql, explanation[:200])
                
            # 7. 更新会话记忆
            self.memory.add_interaction(
                user_message=query,
                assistant_message={
                    "sql": sql,
                    "explanation": explanation,
                    "results_count": row_count
                }
            )
            
            # 8. 构建并返回结果
            query_result = {
                "id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "intent": intent,
                "sql": sql,
                "results": results,
                "row_count": row_count,
                "explanation": explanation,
                "visualization": visualization_config,
                "suggestions": query_suggestions
            }
            
            # 确保结果可以序列化
            return stringify_special_objects(query_result)
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}", exc_info=True)
            # 返回错误信息
            error_result = {
                "id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "error": str(e),
                "message": "执行查询时发生错误，请重试"
            }
            return stringify_special_objects(error_result) 