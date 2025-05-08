"""自然语言到SQL查询链模块

提供将自然语言转换为SQL查询的功能。
"""

import logging
import json
import re
from typing import Any, Dict, List, Optional, Union, cast, Tuple, AsyncGenerator
import sqlalchemy
from sqlalchemy import inspect, text
import time
from datetime import datetime, timedelta
import random
import asyncio

# 延迟导入以下依赖
# from langchain_core.prompts import PromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_community.utilities.sql_database import SQLDatabase
# from langchain.chains.sql_database.prompt import PROMPT, _mysql_prompt, _postgres_prompt, _sqlite_prompt
# from langchain.chains import create_sql_query_chain
# from langchain_core.runnables import RunnablePassthrough

from app.db.session import SyncSessionLocal, sync_engine
from app.services.ai.adapters.langchain_llm import get_langchain_chat_model, LangChainAdapter, extract_content_from_response, ChatOpenRouter
from app.utils.sql_query import SQLQueryTool, get_sql_query_tool
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# 电商数据库表结构描述 - 模拟数据
DEFAULT_DB_SCHEMA = """
电商数据库结构:

1. users (用户表)
   - user_id: INTEGER PRIMARY KEY (用户ID)
   - username: VARCHAR(50) (用户名)
   - email: VARCHAR(100) (电子邮件)
   - phone: VARCHAR(20) (手机号)
   - registration_date: DATETIME (注册日期)
   - last_login: DATETIME (最后登录时间)
   - status: VARCHAR(20) (账户状态: active, inactive, suspended)

2. products (产品表)
   - product_id: INTEGER PRIMARY KEY (产品ID)
   - name: VARCHAR(200) (产品名称)
   - description: TEXT (产品描述)
   - category_id: INTEGER FOREIGN KEY (类别ID, 关联categories表)
   - price: DECIMAL(10,2) (价格)
   - cost: DECIMAL(10,2) (成本)
   - inventory: INTEGER (库存数量)
   - created_at: DATETIME (创建时间)
   - updated_at: DATETIME (更新时间)
   - status: VARCHAR(20) (状态: active, discontinued)

3. categories (产品分类表)
   - category_id: INTEGER PRIMARY KEY (类别ID)
   - name: VARCHAR(100) (类别名称)
   - parent_id: INTEGER (父类别ID, 自关联)
   - description: TEXT (类别描述)

4. orders (订单表)
   - order_id: INTEGER PRIMARY KEY (订单ID)
   - user_id: INTEGER FOREIGN KEY (用户ID, 关联users表)
   - order_date: DATETIME (订单日期)
   - total_amount: DECIMAL(12,2) (订单总金额)
   - status: VARCHAR(20) (状态: pending, paid, shipped, delivered, canceled)
   - shipping_address: TEXT (配送地址)
   - payment_method: VARCHAR(50) (支付方式)

5. order_items (订单项表)
   - item_id: INTEGER PRIMARY KEY (项目ID)
   - order_id: INTEGER FOREIGN KEY (订单ID, 关联orders表)
   - product_id: INTEGER FOREIGN KEY (产品ID, 关联products表)
   - quantity: INTEGER (数量)
   - unit_price: DECIMAL(10,2) (单价)
   - discount: DECIMAL(10,2) (折扣)
   - subtotal: DECIMAL(10,2) (小计)

6. reviews (评价表)
   - review_id: INTEGER PRIMARY KEY (评价ID)
   - product_id: INTEGER FOREIGN KEY (产品ID, 关联products表)
   - user_id: INTEGER FOREIGN KEY (用户ID, 关联users表)
   - rating: INTEGER (评分, 1-5)
   - comment: TEXT (评论内容)
   - review_date: DATETIME (评价日期)
   - helpful_votes: INTEGER (有用票数)

7. inventory_history (库存历史表)
   - history_id: INTEGER PRIMARY KEY (历史记录ID)
   - product_id: INTEGER FOREIGN KEY (产品ID, 关联products表)
   - change_amount: INTEGER (变动数量, 正为入库, 负为出库)
   - change_date: DATETIME (变动日期)
   - reason: VARCHAR(100) (变动原因: purchase, sale, return, adjustment)
   - operator: VARCHAR(50) (操作员)

8. promotions (促销活动表)
   - promotion_id: INTEGER PRIMARY KEY (促销ID)
   - name: VARCHAR(100) (活动名称)
   - description: TEXT (活动描述)
   - discount_type: VARCHAR(20) (折扣类型: percentage, fixed_amount)
   - discount_value: DECIMAL(10,2) (折扣值)
   - start_date: DATETIME (开始日期)
   - end_date: DATETIME (结束日期)
   - active: BOOLEAN (是否激活)

9. returns (退货表)
   - return_id: INTEGER PRIMARY KEY (退货ID)
   - order_id: INTEGER FOREIGN KEY (订单ID, 关联orders表)
   - product_id: INTEGER FOREIGN KEY (产品ID, 关联products表)
   - return_date: DATETIME (退货日期)
   - quantity: INTEGER (数量)
   - reason: TEXT (退货原因)
   - status: VARCHAR(20) (状态: pending, approved, rejected, refunded)
   - refund_amount: DECIMAL(10,2) (退款金额)

10. suppliers (供应商表)
    - supplier_id: INTEGER PRIMARY KEY (供应商ID)
    - name: VARCHAR(100) (供应商名称)
    - contact_person: VARCHAR(50) (联系人)
    - email: VARCHAR(100) (电子邮件)
    - phone: VARCHAR(20) (电话)
    - address: TEXT (地址)
    - status: VARCHAR(20) (状态: active, inactive)

常见关联关系:
- 订单(orders)通过user_id关联用户(users)
- 订单项(order_items)通过order_id关联订单(orders)
- 订单项(order_items)通过product_id关联产品(products)
- 产品(products)通过category_id关联类别(categories)
- 评价(reviews)通过product_id关联产品(products)和通过user_id关联用户(users)
- 退货(returns)通过order_id关联订单(orders)和通过product_id关联产品(products)
- 库存历史(inventory_history)通过product_id关联产品(products)
"""

# 生成基本的SQL查询的提示模板
SQL_GENERATION_PROMPT = """
你是一位电商数据分析专家，负责将自然语言查询转换为SQL查询并提供后续查询建议。

## 任务说明
你的任务有两个部分：
1. 为自然语言查询生成两个SQL查询：
   - 主要SQL：完整、优化的查询，能够精确满足用户需求
   - 备用SQL：简化版本的查询，当主要查询因复杂性或特定函数不兼容而失败时使用
2. 提供3个相关的后续查询建议，帮助用户进一步探索数据

## 数据库表结构
{db_schema}

## SQL查询要求
- 主要SQL应该尽可能完整地满足用户需求
- 备用SQL应该更简单但仍能提供有用信息
- 使用清晰的列名、表连接和有意义的别名
- 限制结果为100行(除非明确要求更多)
- 使用标准SQL函数(COUNT, SUM, AVG, MAX, MIN等)

## 后续查询建议要求
- 提供3个相关且有深度的后续查询建议
- 建议应该基于当前查询的结果，引导用户深入探索
- 每个建议应以自然语言形式呈现，以问号结尾
- 建议应该具有业务价值，帮助用户发现更多洞察

## 示例
查询: 销量最高的3个产品是什么？

-- 主要SQL
SELECT p.product_id, p.name AS product_name, SUM(oi.quantity) AS total_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.name
ORDER BY total_sold DESC
LIMIT 3;

-- 备用SQL
SELECT product_id, name AS product_name
FROM products
ORDER BY product_id
LIMIT 5;

-- 后续查询建议
1. 这些热销产品的客户评价如何？
2. 销量最高的产品在不同季节的销售趋势如何？
3. 这些产品的利润率与其他产品相比如何？

## 当前查询
{query}

## 输出格式
请严格按照以下格式输出：

```sql
-- 主要SQL
SELECT ...

-- 备用SQL
SELECT ...

-- 后续查询建议
1. [第一个建议]
2. [第二个建议]
3. [第三个建议]
```
"""

# 解释SQL查询结果的提示模板
SQL_EXPLANATION_PROMPT = """
你是一位电商数据分析专家，负责解释SQL查询结果并提供业务洞察。请分析以下信息：

## 查询背景
原始查询: {query}
SQL查询: {sql}

## 查询结果
{results}

## 分析框架
请提供结构化分析，包含以下部分：

### 1. 结果摘要
用1-2个简短段落总结关键发现，强调最重要的数据点和直接可见的模式。

### 2. 关键发现与业务洞察
列出3-5个主要洞察，每个包含：
- 具体数据点或模式
- 可能的业务含义
- 与行业标准或历史数据的对比（如适用）

### 3. 数据模式与趋势
分析数据中的：
- 分布特征（如集中度、离散度）
- 异常值及其可能含义
- 相关性和模式（如不同维度间的关系）
- 季节性或周期性特征（如适用）

### 4. 建议与行动点
提供3-5个基于数据的具体建议：
- 具体、可执行的业务行动
- 需要进一步分析的方向
- 潜在风险和机会

分析应专业、简洁且富有洞察力，避免使用过于技术性的语言，确保业务人员容易理解。
重点关注对业务决策有实际价值的信息，而非简单描述数据。
"""

# 生成可视化建议的提示模板
VISUALIZATION_PROMPT = """
作为数据可视化专家，请为以下查询结果推荐最合适的可视化方式。

## 查询信息
原始查询: {query}
SQL查询: {sql}

## 数据结构
查询结果结构:
{schema}

查询结果示例数据:
{sample_data}

## 图表类型与适用场景
- 折线图: 适用于时间序列数据、趋势分析
- 柱状图: 适用于分类比较、排名分析
- 条形图: 适用于水平比较、长文本标签
- 饼图/环形图: 适用于占比分析（不超过7个分类）
- 散点图: 适用于相关性分析、分布分析
- 面积图: 适用于堆叠数据、累积值展示
- 热力图: 适用于矩阵数据、密度分布
- 雷达图: 适用于多维度对比
- 漏斗图: 适用于流程转化率
- 表格: 适用于精确数值、多维度数据

## 智能图表选择指南
1. 时间数据: 首选折线图或面积图
2. 分类对比: 首选柱状图或条形图
3. 部分与整体: 首选饼图或环形图
4. 相关性分析: 首选散点图
5. 复杂数据: 首选表格或组合图表
6. 地理数据: 首选地图
7. 单一数值: 首选仪表盘或进度条

## 返回格式说明
请以JSON格式返回一个可视化配置对象，包含以下字段:
- chart_type: 图表类型(支持: "line", "bar", "horizontal-bar", "pie", "scatter", "area", "heatmap", "radar", "funnel", "table")
- title: 图表标题(简明扼要描述图表内容)
- description: 图表解释(为什么选择这种图表类型)
- x_axis: X轴数据字段(如适用)
- y_axis: Y轴数据字段或数组(如适用)
- category: 分类字段(如适用)
- series: 系列数据字段(如适用)
- color_by: 着色字段(如适用)
- aggregation: 聚合方式(如适用，例如"sum", "avg", "count")
- format: 数值格式化(如适用，例如"percent", "currency", "number")
- sort_by: 排序字段(如适用)
- sort_order: 排序方式(如适用，"asc"或"desc")
- limit: 显示的最大数据点数量(如适用)

仅返回JSON格式的配置对象，不要包含其他内容。
"""

# 生成后续查询建议的提示模板
SUGGESTION_PROMPT = """
作为电商数据分析助手，请根据用户的当前查询和结果，推荐3-5个有价值的后续查询问题。

## 当前分析上下文
用户当前查询: {query}
SQL查询: {sql}
查询结果摘要: {summary}

## 后续查询建议策略
推荐能够深入探索、拓展分析或揭示更多洞察的后续问题。建议应该遵循以下原则：

1. **递进深度原则**：从当前结果深入一层，挖掘潜在原因或更细节的信息
   例如：当前查询"销量最高的产品"→建议"这些产品的客户评价如何？"

2. **维度拓展原则**：在保持主题相关性的前提下，增加新的分析维度
   例如：当前查询"各地区销售额"→建议"各地区的客户忠诚度如何？"

3. **趋势探索原则**：提供时间维度的变化分析
   例如：当前查询"本月利润率"→建议"过去12个月的利润率趋势如何？" 

4. **异常解释原则**：针对当前结果中的特殊点提出解释性问题
   例如：当前查询显示某产品突然增长→建议"导致产品X销售增长的因素是什么？"

5. **业务行动原则**：引导向可执行的业务决策
   例如：当前查询"退货率高的产品"→建议"如何优化这些产品以减少退货？"

## 问题类型参考
- **描述性问题**："什么是...？" "有多少...？" "哪些...？"
- **比较性问题**："与...相比如何？" "...之间有什么差异？"
- **关联性问题**："...与...之间有什么关系？" "...会影响...吗？"
- **预测性问题**："未来...趋势如何？" "如果...会发生什么？"
- **行动性问题**："如何改善...？" "应该采取什么措施...？"

请提供3-5个自然语言形式的后续查询建议，确保它们直接相关且有分析深度，能为业务决策提供有价值的洞察。
每个建议应简洁明了，直接以问句形式呈现，避免重复，并确保能通过SQL实现。
"""

class DatabaseToolkit:
    """数据库工具类，用于提供数据库元数据和执行查询"""
    
    def __init__(
        self,
        engine: Optional[sqlalchemy.engine.Engine] = None,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        sql_query_tool: Optional[Any] = None
    ):
        """
        初始化数据库工具类
        
        Args:
            engine: 数据库引擎
            include_tables: 要包含的表列表
            exclude_tables: 要排除的表列表
            sample_rows_in_table_info: 表信息示例行数
            sql_query_tool: 自定义SQL查询工具，如果提供则使用此工具
        """
        self.sample_rows_in_table_info = sample_rows_in_table_info
        self.include_tables = include_tables
        self.exclude_tables = exclude_tables
        
        # 使用提供的SQL查询工具或创建新的工具
        if sql_query_tool:
            self.sql_query_tool = sql_query_tool
        else:
            from app.utils.sql_query import get_sql_query_tool
            self.sql_query_tool = get_sql_query_tool(
                read_only=True,
                allowed_tables=include_tables,  # 传递允许的表列表
                restricted_tables=exclude_tables  # 传递限制的表列表
            )
        
        # 创建SQLAlchemy数据库实例
        try:
            # 尝试创建SQLDatabase
            try:
                # 尝试最新版本的langchain导入
                try:
                    from langchain_community.utilities import SQLDatabase
                    self.db = SQLDatabase(engine=self.sql_query_tool.engine)
                except (ImportError, AttributeError, TypeError):
                    # 尝试旧版本的langchain导入
                    try:
                        from langchain.utilities import SQLDatabase
                        self.db = SQLDatabase(engine=self.sql_query_tool.engine)
                    except (ImportError, AttributeError, TypeError):
                        # 最后尝试原始版本
                        from langchain.utilities.sql_database import SQLDatabase
                        self.db = SQLDatabase(self.sql_query_tool.engine)
            except Exception as e:
                logger.warning(f"无法创建SQLDatabase: {str(e)}，某些功能将不可用")
                self.db = None
        except ImportError:
            logger.warning("无法导入SQLDatabase，某些功能将不可用")
            self.db = None
        
        # 保存引擎引用
        self.engine = self.sql_query_tool.engine if self.sql_query_tool else engine
    
    def get_database_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取数据库表模式详细信息
        
        Returns:
            数据库表结构的字典，键为表名，值为列定义列表
        """
        try:
            # 使用SQL查询工具获取数据库表结构
            tables_info = {}
            
            # 获取所有表名
            table_names = self.get_table_names()
            
            # 根据包含/排除过滤表
            if self.include_tables:
                table_names = [t for t in table_names if t in self.include_tables]
            if self.exclude_tables:
                table_names = [t for t in table_names if t not in self.exclude_tables]
            
            # 获取每个表的结构
            for table_name in table_names:
                try:
                    schema_info = self.sql_query_tool.get_table_schema(table_name)
                    
                    if not schema_info.get("success", False):
                        logger.warning(f"获取表 {table_name} 结构失败: {schema_info.get('error', '未知错误')}")
                        continue
                    
                    # 提取列信息
                    columns = []
                    for col in schema_info.get("columns", []):
                        column_info = {
                            "name": col["name"],
                            "type": col["type"],
                            "primary_key": col.get("primary_key", False),
                            "nullable": col.get("nullable", True),
                            "description": f"{col['name']} ({col['type']})"
                        }
                        
                        # 添加外键信息
                        for fk in schema_info.get("foreign_keys", []):
                            if col["name"] in fk["constrained_columns"]:
                                column_info["foreign_key"] = f"{fk['referred_table']}.{','.join(fk['referred_columns'])}"
                                break
                        
                        columns.append(column_info)
                    
                    tables_info[table_name] = columns
                    
                except Exception as e:
                    logger.error(f"获取表 {table_name} 结构时出错: {str(e)}")
            
            return tables_info
            
        except Exception as e:
            logger.error(f"获取数据库模式失败: {str(e)}")
            return {}
    
    def get_schema_description(self) -> str:
        """
        获取数据库Schema的详细描述
        
        Returns:
            数据库Schema的详细描述字符串
        """
        if self.db:
            return self.db.get_table_info()
        else:
            return "SQLDatabase未初始化，无法获取Schema描述"
    
    def get_table_names(self) -> List[str]:
        """
        获取数据库中所有表名
        
        Returns:
            表名列表
        """
        if self.db:
            metadata = sqlalchemy.MetaData()
            metadata.reflect(bind=self.sql_query_tool.engine)
            return list(metadata.tables.keys())
        else:
            return []
    
    def get_table_description(self, table_name: str) -> str:
        """
        获取特定表的结构描述
        
        Args:
            table_name: 表名
            
        Returns:
            表结构描述字符串
        """
        # 使用SQL查询工具获取表结构
        schema_info = self.sql_query_tool.get_table_schema(table_name)
        
        if not schema_info.get("success", False):
            return f"无法获取表 {table_name} 的结构: {schema_info.get('error', '未知错误')}"
        
        # 构建描述字符串
        description = f"Table '{table_name}':\n"
        
        # 添加列信息
        for column in schema_info.get("columns", []):
            description += f"- {column['name']} ({column['type']})"
            if column.get("primary_key"):
                description += " (PK)"
            if not column.get("nullable"):
                description += " (NOT NULL)"
            description += "\n"
        
        # 添加外键信息
        foreign_keys = schema_info.get("foreign_keys", [])
        if foreign_keys:
            description += "\nForeign Keys:\n"
            for fk in foreign_keys:
                description += f"- {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}\n"
        
        # 添加索引信息
        indexes = schema_info.get("indexes", [])
        if indexes:
            description += "\nIndexes:\n"
            for idx in indexes:
                description += f"- {idx['name']} on ({', '.join(idx['columns'])})"
                if idx.get("unique"):
                    description += " UNIQUE"
                description += "\n"
        
        return description
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            query: SQL查询语句
            
        Returns:
            查询结果列表
        """
        # 使用SQL查询工具执行查询
        start_time = time.perf_counter()
        try:
            result = self.sql_query_tool.execute_query(query)
            execution_time = time.perf_counter() - start_time
            
            if isinstance(result, dict) and "data" in result:
                # 新版API返回的是结构化结果对象
                logger.info(f"查询执行成功，耗时: {execution_time:.4f}秒，返回{len(result['data'])}行结果")
                return result["data"]
            elif hasattr(result, "data") and hasattr(result, "success"):
                # 新版API返回的是结构化结果对象（实例）
                if result.success:
                    logger.info(f"查询执行成功，耗时: {execution_time:.4f}秒，返回{len(result.data)}行结果")
                    return result.data
                else:
                    logger.error(f"查询执行失败: {result.error}")
                    # 返回空结果列表，避免None值错误
                    return []
            elif isinstance(result, list):
                # 返回的是直接结果列表
                logger.info(f"查询执行成功，耗时: {execution_time:.4f}秒，返回{len(result)}行结果")
                return result
            else:
                # 不支持的返回类型
                logger.warning(f"不支持的查询结果类型: {type(result)}")
                return []
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(f"执行查询时出错: {str(e)}, 耗时: {execution_time:.4f}秒")
            # 出错时返回空列表而不是None
            return []
            
    


class NL2SQLChain:
    """自然语言到SQL转换链
    
    将自然语言查询转换为SQL查询，执行查询并返回结果。
    """
    
    def __init__(
        self, 
        database_toolkit = None,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
        config: Dict[str, bool] = None
    ):
        """初始化NL2SQL链
        
        Args:
            database_toolkit: 数据库工具包
            include_tables: 包含的表列表
            exclude_tables: 排除的表列表
            config: 配置参数
        """
        # 设置默认配置
        self.config = {
            "need_explanation": True,  # 是否需要解释
            "need_visualization": True,  # 是否需要可视化配置
            "need_suggestions": True,   # 是否需要建议
        }
        
        # 更新配置
        if config:
            self.config.update(config)
            
        # 使用新的ChatOpenRouter类初始化LLM适配器
        try:
            self.llm_adapter = LangChainAdapter(
                model_name=settings.DEEPSEEK_MODEL if settings.DEFAULT_AI_MODEL.lower() == "deepseek" else settings.OPENROUTER_MODEL,
                temperature=0.1  # 使用较低的温度以获得更确定性的结果
            )
            logger.info("NL2SQL链成功初始化LLM适配器")
        except Exception as e:
            logger.error(f"初始化LLM适配器失败: {str(e)}")
            self.llm_adapter = None
        
        # 初始化数据库工具
        if database_toolkit:
            self.database_toolkit = database_toolkit
        else:
            try:
                # 创建新的数据库工具包
                self.database_toolkit = DatabaseToolkit(
                    include_tables=include_tables,
                    exclude_tables=exclude_tables
                )
                logger.info("NL2SQL查询链初始化成功")
            except Exception as e:
                logger.error(f"NL2SQL查询链初始化失败: {str(e)}")
                self.database_toolkit = None
        
        # SQL链是否可用标志
        self.sql_chain = self.database_toolkit is not None and self.llm_adapter is not None
            
        # 缓存实际的数据库模式
        self._db_schema = None
    
    def validate_sql_query(self, sql_query: str) -> Tuple[bool, str]:
        """
        验证SQL查询的语法和结构正确性
        
        Args:
            sql_query: 待验证的SQL查询
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 基本语法检查
            if not sql_query or len(sql_query.strip()) < 10:
                return False, "SQL查询为空或过短"
                
            # 检查必要关键字
            if "SELECT" not in sql_query.upper():
                return False, "缺少SELECT语句"
                
            # 检查表名对应
            if self.database_toolkit:
                all_tables = self.database_toolkit.get_table_names()
                for table in all_tables:
                    # 统一小写比较
                    table_lower = table.lower()
                    if table_lower in sql_query.lower() and table not in sql_query:
                        return False, f"表名'{table}'大小写不匹配"
                    
            return True, ""
        except Exception as e:
            return False, f"验证SQL时出错: {str(e)}"
    
    def get_schema_description(self) -> str:
        """
        获取数据库模式描述
        
        Returns:
            数据库模式描述字符串
        """
        # 尝试获取真实数据库表结构
        if not self._db_schema and self.database_toolkit and self.database_toolkit.engine:
            try:
                # 获取实际数据库表列表
                tables = []
                inspector = inspect(self.database_toolkit.engine)
                tables = inspector.get_table_names()
                
                if not tables:
                    logger.warning("数据库中未找到任何表，使用默认表结构")
                    return DEFAULT_DB_SCHEMA
                
                # 构建表结构描述
                schema_text = "数据库表结构:\n\n"
                
                for table_name in tables:
                    schema_text += f"{table_name} 表:\n"
                    
                    try:
                        # 获取列信息
                        columns = inspector.get_columns(table_name)
                        for col in columns:
                            col_type = str(col["type"])
                            schema_text += f"  - {col['name']}: {col_type} "
                            if col.get('primary_key', False):
                                schema_text += "(主键) "
                            if col.get('nullable') is False:
                                schema_text += "(非空) "
                            schema_text += "\n"
                        
                        # 获取主键信息
                        try:
                            pk = inspector.get_pk_constraint(table_name)
                            if pk and 'constrained_columns' in pk and pk['constrained_columns']:
                                schema_text += f"  主键: {', '.join(pk['constrained_columns'])}\n"
                        except Exception as e:
                            logger.warning(f"获取表 {table_name} 主键信息时出错: {str(e)}")
                        
                        # 获取外键信息
                        try:
                            fks = inspector.get_foreign_keys(table_name)
                            if fks:
                                schema_text += "  外键关系:\n"
                                for fk in fks:
                                    schema_text += f"    - {', '.join(fk.get('constrained_columns', []))} -> {fk.get('referred_table')}.{', '.join(fk.get('referred_columns', []))}\n"
                        except Exception as e:
                            logger.warning(f"获取表 {table_name} 外键信息时出错: {str(e)}")
                        
                        schema_text += "\n"
                    except Exception as e:
                        logger.error(f"获取表 {table_name} 结构时出错: {str(e)}")
                        schema_text += f"  (获取表结构失败: {str(e)})\n\n"
                
                # 缓存结果
                self._db_schema = schema_text
                logger.info(f"成功获取真实数据库表结构信息，包含 {len(tables)} 个表")
                return schema_text
                
            except Exception as e:
                logger.error(f"获取数据库模式失败，使用默认模式: {str(e)}")
        
        # 如果已经缓存了表结构，直接返回
        if self._db_schema:
            return self._db_schema
            
        # 如果上述尝试都失败，返回默认模式
        return DEFAULT_DB_SCHEMA
        
    async def execute_query(self, sql_query: str) -> Tuple[List[Dict], int]:
        """
        执行SQL查询
        
        Args:
            sql_query: SQL查询语句
            
        Returns:
            (结果列表, 结果数量)
        """
        # 无论设置如何，始终使用真实数据库查询
        try:
            # 真实模式下执行SQL查询
            if self.database_toolkit and sql_query:
                # 验证SQL是否正确
                is_valid, error_msg = self.validate_sql_query(sql_query)
                if not is_valid:
                    logger.warning(f"SQL查询无效: {error_msg}")
                    return [], 0
                
                # 测试SQL是否可以执行
                safe_sql = self._ensure_safe_sql(sql_query)
                
                # 记录查询开始
                logger.info(f"执行SQL查询: {safe_sql}")
                start_time = time.perf_counter()
                
                results = self.database_toolkit.execute_query(safe_sql)
                
                # 记录结果行数
                row_count = len(results) if results else 0
                elapsed = time.perf_counter() - start_time
                logger.info(f"查询执行完成，返回 {row_count} 条真实数据，耗时 {elapsed:.2f}秒")
                
                # 确保结果不会太大
                if row_count > 100:
                    results = results[:100]  # 只返回前100行
                    logger.info("结果被截断为前100行")
                    
                # 验证结果格式
                if results and isinstance(results, list) and not isinstance(results[0], dict):
                    logger.warning(f"查询结果格式异常: {type(results[0])}")
                    # 尝试转换为字典列表
                    if hasattr(results[0], "_asdict"):  # 处理命名元组
                        results = [dict(row._asdict()) for row in results]
                    else:
                        # 最后尝试将结果转为JSON再解析回来规范化格式
                        results = json.loads(json.dumps(results))
                
                # 转换所有内容为可序列化格式
                results = self._format_results(results)
                
                return results, row_count
            else:
                logger.error("数据库工具不可用或SQL查询为空")
                return [], 0
                
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            # 失败时返回空结果
            return [], 0
    
    async def generate_sql_with_suggestions(self, query: str) -> Tuple[str, List[str]]:
        """
        根据自然语言查询生成SQL查询和后续查询建议
        
        Args:
            query: 自然语言查询
            
        Returns:
            (SQL查询字符串, 建议列表)元组
        """
        start_time = time.perf_counter()
        
        # 如果查询为空，直接返回
        if not query or len(query.strip()) < 3:
            return "", []
            
        # 重试机制
        max_retries = 2  # 最大重试次数
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    logger.info(f"SQL生成重试 #{retry_count}")
                
                if self.sql_chain and self.llm_adapter:
                    # 使用LangChain生成SQL
                    logger.info(f"生成SQL查询和建议: {query}")
                    
                    # 获取数据库表结构描述
                    db_schema = self.get_schema_description()
                    
                    # 构建完整提示词
                    prompt = SQL_GENERATION_PROMPT.format(
                        db_schema=db_schema,
                        query=query
                    )
                    
                    # 调用LLM生成SQL
                    try:
                        sql_response = await self.llm_adapter.generate(
                            prompt=prompt,
                            max_tokens=2000  # 增加token上限，因为现在需要生成SQL和建议
                        )
                        
                        # 检查响应是否为空
                        if sql_response is None or not isinstance(sql_response, str) or sql_response.strip() == "":
                            logger.warning(f"LLM返回了空响应或无效响应，重试 ({retry_count}/{max_retries})")
                            retry_count += 1
                            if retry_count > max_retries:
                                logger.warning("已达到最大重试次数，使用回退SQL生成")
                                return await self._fallback_sql_generation(query), self._generate_default_suggestions(query)
                            # 添加短暂等待，避免立即重试
                            await asyncio.sleep(1.5)
                            continue
                            
                        logger.debug(f"LLM原始响应: {sql_response}")
                        
                        # 从响应中提取主要SQL、备用SQL和建议
                        main_sql, fallback_sql, suggestions = self._extract_sql_pair(sql_response)
                        
                        logger.debug(f"提取的主要SQL: {main_sql}")
                        logger.debug(f"提取的备用SQL: {fallback_sql}")
                        logger.debug(f"提取的后续查询建议: {suggestions}")
                        
                        # 尝试使用主要SQL
                        if main_sql:
                            # 验证主要SQL
                            is_valid, error_msg = self.validate_sql_query(main_sql)
                            if is_valid:
                                elapsed_time = time.perf_counter() - start_time
                                logger.info(f"SQL生成耗时: {elapsed_time:.4f}秒，使用主要SQL")
                                return main_sql, suggestions
                            else:
                                logger.warning(f"主要SQL无效: {error_msg}")
                        
                        # 尝试使用备用SQL
                        if fallback_sql:
                            # 验证备用SQL
                            is_valid, error_msg = self.validate_sql_query(fallback_sql)
                            if is_valid:
                                elapsed_time = time.perf_counter() - start_time
                                logger.info(f"SQL生成耗时: {elapsed_time:.4f}秒，使用备用SQL")
                                return fallback_sql, suggestions
                            else:
                                logger.warning(f"备用SQL也无效: {error_msg}")
                        
                    except Exception as e:
                        logger.error(f"LLM调用失败: {str(e)}")
                        retry_count += 1
                        if retry_count > max_retries:
                            logger.warning("已达到最大重试次数，使用回退SQL生成")
                            return await self._fallback_sql_generation(query), self._generate_default_suggestions(query)
                        # 添加短暂等待，避免立即重试
                        await asyncio.sleep(1.5)
                        continue
                
                    # 如果提取失败或SQL都无效，尝试再次重试
                    logger.warning(f"无法从LLM响应中提取有效SQL ({retry_count}/{max_retries})")
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.warning("已达到最大重试次数，使用回退SQL生成")
                        return await self._fallback_sql_generation(query), self._generate_default_suggestions(query)
                    await asyncio.sleep(1.5)
                    continue
                    
                else:
                    # 链不可用，使用回退方法
                    if not self.llm_adapter:
                        logger.warning("LLM适配器不可用，使用回退方法")
                    else:
                        logger.warning("SQL生成链不可用，使用回退方法")
                    return await self._fallback_sql_generation(query), self._generate_default_suggestions(query)
                
            except Exception as e:
                logger.error(f"LLM SQL生成失败: {str(e)}, 尝试重试 ({retry_count}/{max_retries})")
                retry_count += 1
                if retry_count > max_retries:
                    logger.warning("已达到最大重试次数，使用回退SQL生成")
                    elapsed_time = time.perf_counter() - start_time
                    logger.info(f"回退SQL生成耗时: {elapsed_time:.4f}秒")
                    return await self._fallback_sql_generation(query), self._generate_default_suggestions(query)
                # 添加短暂等待，避免立即重试
                await asyncio.sleep(1.5)
    
        # 如果所有重试都失败，使用回退方法
        return await self._fallback_sql_generation(query), self._generate_default_suggestions(query)

    async def generate_sql(self, query: str) -> str:
        """
        根据自然语言查询生成SQL查询（兼容旧接口）
        
        Args:
            query: 自然语言查询
            
        Returns:
            SQL查询字符串
        """
        sql, _ = await self.generate_sql_with_suggestions(query)
        return sql
    
    def _extract_sql_pair(self, sql_response: str) -> Tuple[str, str, List[str]]:
        """
        从LLM响应中提取主要SQL、备用SQL和后续查询建议
        
        Args:
            sql_response: LLM响应
            
        Returns:
            (主要SQL, 备用SQL, 后续查询建议)元组
        """
        # 初始化结果
        main_sql = ""
        fallback_sql = ""
        suggestions = []
        
        try:
            # 使用正则表达式提取SQL代码块
            # 标记模式
            main_pattern = r'--\s*主要SQL\s*\n([\s\S]*?)(?=--\s*备用SQL|\Z)'
            fallback_pattern = r'--\s*备用SQL\s*\n([\s\S]*?)(?=--\s*后续查询建议|\Z)'
            suggestions_pattern = r'--\s*后续查询建议\s*\n([\s\S]*?)(?=```|\Z)'
            
            # 旧格式: 寻找"主要SQL"和"备用SQL"的模式
            old_main_pattern = r'主要SQL[：:]\s*```sql\s*(.*?)\s*```'
            old_fallback_pattern = r'备用SQL[：:]\s*```sql\s*(.*?)\s*```'
            
            # 通用代码块模式（以防其他格式不匹配）
            generic_pattern = r'```sql\s*([\s\S]*?)\s*```'
            
            # 1. 首先尝试匹配新格式
            # 找到SQL代码块
            code_blocks = re.findall(r'```sql\s*([\s\S]*?)\s*```', sql_response, re.DOTALL)
            if code_blocks:
                # 在代码块内查找标记的SQL
                for block in code_blocks:
                    main_match = re.search(main_pattern, block, re.DOTALL)
                    fallback_match = re.search(fallback_pattern, block, re.DOTALL)
                    suggestions_match = re.search(suggestions_pattern, block, re.DOTALL)
                    
                    if main_match:
                        main_sql = main_match.group(1).strip()
                    if fallback_match:
                        fallback_sql = fallback_match.group(1).strip()
                    if suggestions_match:
                        suggestions_text = suggestions_match.group(1).strip()
                        # 提取每行建议
                        for line in suggestions_text.split('\n'):
                            # 去除序号和前导空白
                            clean_line = re.sub(r'^\d+\.?\s*', '', line.strip())
                            if clean_line and (clean_line.endswith('?') or clean_line.endswith('？')):
                                suggestions.append(clean_line)
                    
                    # 如果在一个代码块中找到了所有内容，就不再继续查找
                    if main_sql and fallback_sql and suggestions:
                        break
            
            # 2. 如果新格式未匹配成功，尝试直接在整个响应中查找
            if not main_sql or not fallback_sql:
                main_match = re.search(main_pattern, sql_response, re.DOTALL)
                fallback_match = re.search(fallback_pattern, sql_response, re.DOTALL)
                
                if main_match:
                    main_sql = main_match.group(1).strip() 
                if fallback_match:
                    fallback_sql = fallback_match.group(1).strip()
            
            # 尝试在整个响应中查找建议
            if not suggestions:
                suggestions_match = re.search(suggestions_pattern, sql_response, re.DOTALL)
                if suggestions_match:
                    suggestions_text = suggestions_match.group(1).strip()
                    # 提取每行建议
                    for line in suggestions_text.split('\n'):
                        # 去除序号和前导空白
                        clean_line = re.sub(r'^\d+\.?\s*', '', line.strip())
                        if clean_line and (clean_line.endswith('?') or clean_line.endswith('？')):
                            suggestions.append(clean_line)
                
                # 也可以尝试从代码块外部提取建议
                if not suggestions:
                    outside_suggestions = re.findall(r'\d+\.\s*(.*?[?？])', sql_response, re.DOTALL)
                    for suggestion in outside_suggestions:
                        if suggestion.strip():
                            suggestions.append(suggestion.strip())
                
            # 3. 如果新格式未匹配成功，尝试旧格式
            if not main_sql or not fallback_sql:
                # 尝试匹配旧格式
                old_main_match = re.search(old_main_pattern, sql_response, re.DOTALL)
                old_fallback_match = re.search(old_fallback_pattern, sql_response, re.DOTALL)
                
                if old_main_match and not main_sql:
                    main_sql = old_main_match.group(1).strip()
                if old_fallback_match and not fallback_sql:
                    fallback_sql = old_fallback_match.group(1).strip()
                    
            # 4. 如果都未匹配成功，尝试从通用代码块中提取
            if not main_sql and not fallback_sql:
                generic_matches = re.findall(generic_pattern, sql_response, re.DOTALL)
                if generic_matches:
                    # 使用第一个代码块作为主要SQL
                    main_sql = generic_matches[0].strip()
                    # 如果有第二个代码块，使用它作为备用SQL
                    if len(generic_matches) > 1:
                        fallback_sql = generic_matches[1].strip()
            
            # 如果没有找到足够的建议，使用默认建议
            if len(suggestions) < 3:
                default_suggestions = self._generate_default_suggestions(main_sql or fallback_sql)
                # 补充到3个建议
                while len(suggestions) < 3 and default_suggestions:
                    suggestions.append(default_suggestions.pop(0))
                    
            # 限制建议数量为3-5个
            suggestions = suggestions[:5]
            
            return main_sql, fallback_sql, suggestions
            
        except Exception as e:
            logger.error(f"提取SQL和建议失败: {str(e)}")
            return main_sql, fallback_sql, []
    
    async def explain_results(self, query: str, sql: str, results: List[Dict]) -> str:
        """
        解释查询结果
        
        Args:
            query: 原始自然语言查询
            sql: 执行的SQL查询
            results: 查询结果
            
        Returns:
            解释文本
        """
        # 如果配置中禁用了解释功能，直接返回简单描述
        if not self.config.get("need_explanation", True):
            logger.info("根据配置，跳过生成查询解释")
            return f"查询返回了{len(results)}条结果。"
        
        # 如果结果为空，返回简单解释
        if not results:
            return "查询未返回任何结果。这可能是因为数据库中没有符合条件的数据，或者查询条件过于严格。"
            
        try:
            # 检查LLM适配器是否可用
            if not self.llm_adapter:
                logger.warning("LLM适配器不可用，使用默认解释方法")
                return self._generate_default_explanation(query, results)
            
            # 提取结果模式
            schema = []
            if results and isinstance(results[0], dict):
                # 获取所有列名
                try:
                    columns = list(results[0].keys())
                except (AttributeError, TypeError, IndexError) as e:
                    logger.error(f"提取列名时出错: {str(e)}")
                    return self._generate_default_explanation(query, results)
            
            # 生成示例数据
            sample_data = json.dumps(results[:5], ensure_ascii=False, indent=2)
            
            # 构建提示词
            prompt = SQL_EXPLANATION_PROMPT.format(
                query=query,
                sql=sql,
                results=sample_data
            )
            
            # 调用LLM生成解释
            try:
                logger.info("开始生成查询解释...")
                start_time = time.perf_counter()
                
                explanation = await self.llm_adapter.generate(
                    prompt=prompt,
                    max_tokens=1024
                )
                
                elapsed = time.perf_counter() - start_time
                logger.info(f"查询解释生成完成，耗时: {elapsed:.2f}秒")
                
                # 检查响应是否为空
                if explanation is None or not isinstance(explanation, str) or explanation.strip() == "":
                    logger.warning("LLM返回了空响应或无效响应，无法生成解释")
                    return self._generate_default_explanation(query, results)
                    
                logger.debug(f"LLM解释原始响应: {explanation[:500]}...")
            except Exception as e:
                logger.error(f"LLM解释生成失败: {str(e)}")
                return self._generate_default_explanation(query, results)
            
            # 验证解释内容是否有效
            if not explanation or explanation.strip() == "":
                return self._generate_default_explanation(query, results)
            
            return explanation
            
        except Exception as e:
            logger.error(f"生成查询解释失败: {str(e)}")
            return self._generate_default_explanation(query, results)
    
    def _generate_default_explanation(self, query: str, results: List[Dict]) -> str:
        """
        生成默认的查询解释，当LLM生成失败时使用
        
        Args:
            query: 自然语言查询
            results: 查询结果
            
        Returns:
            默认解释文本
        """
        # 如果结果为空
        if len(results) == 0:
            return "查询未返回任何结果。这可能是因为数据库中没有符合条件的数据，或者查询条件过于严格。"
        
        # 如果是聚合查询结果(单行带聚合值的结果)
        if len(results) == 1 and any(k.lower().startswith(('sum_', 'avg_', 'count_', 'max_', 'min_')) or 
                                    k.lower() in ('total', 'average', 'count', 'minimum', 'maximum', 'monthly_sales') 
                                    for k in results[0].keys()):
            agg_values = []
            for k, v in results[0].items():
                agg_values.append(f"{k}: {v}")
            
            result_text = ", ".join(agg_values)
            return f"查询结果包含以下聚合值: {result_text}"
        
        # 普通查询结果
        return f"查询返回了{len(results)}条结果。" + (
            f"展示的数据包含以下字段: {', '.join(results[0].keys())}" if results else ""
        )
    
    async def generate_visualization_config(self, query: str, sql: str, results: List[Dict]) -> Dict:
        """
        生成可视化配置
        
        Args:
            query: 原始自然语言查询
            sql: 执行的SQL查询
            results: 查询结果
            
        Returns:
            可视化配置
        """
        # 如果配置中禁用了可视化功能，直接返回简单的表格配置
        if not self.config.get("need_visualization", True):
            logger.info("根据配置，跳过生成可视化配置")
            return {"chart_type": "table", "title": "查询结果", "description": "简单表格展示"}
        
        if not results:
            return {
                "chart_type": "table",
                "title": "查询未返回数据",
                "message": "无数据可视化"
            }
            
        try:
            # 检查LLM适配器是否可用
            if not self.llm_adapter:
                logger.warning("LLM适配器不可用，使用智能推断可视化配置")
                return self._infer_visualization_config(query, results)
            
            # 提取结果模式
            schema = []
            if results and isinstance(results[0], dict):
                for key in results[0].keys():
                    schema.append(key)
                    
            schema_str = ", ".join(schema)
            
            # 生成示例数据
            sample_data = json.dumps(results[:3], ensure_ascii=False, indent=2)
            
            # 构建提示词
            prompt = VISUALIZATION_PROMPT.format(
                query=query,
                sql=sql,
                columns=schema_str,
                results_sample=sample_data
            )
            
            # 调用LLM生成可视化配置
            try:
                logger.info("开始生成可视化配置...")
                start_time = time.perf_counter()
                
                config_str = await self.llm_adapter.generate(
                    prompt=prompt,
                    max_tokens=1024
                )
                
                elapsed = time.perf_counter() - start_time
                logger.info(f"可视化配置生成完成，耗时: {elapsed:.2f}秒")
                
                # 检查响应是否为空
                if config_str is None or not isinstance(config_str, str) or config_str.strip() == "":
                    logger.warning("LLM返回了空响应或无效响应，无法生成可视化配置")
                    return self._infer_visualization_config(query, results)
                    
                logger.debug(f"LLM可视化配置原始响应: {config_str[:300]}...")
            except Exception as e:
                logger.error(f"LLM可视化配置生成失败: {str(e)}")
                return self._infer_visualization_config(query, results)
            
            # 尝试提取和解析JSON
            config_json = self._extract_json_from_text(config_str)
            
            # 如果解析失败，尝试智能推断配置
            if not config_json:
                logger.warning("无法提取有效的JSON配置，将智能推断配置")
                config_json = self._infer_visualization_config(query, results)
                
            # 加入默认值
            if "chart_type" not in config_json:
                config_json["chart_type"] = "table"
            if "title" not in config_json:
                config_json["title"] = "查询结果可视化"
                
            return config_json
                
        except Exception as e:
            logger.error(f"生成可视化配置失败: {str(e)}")
            # 返回默认表格配置
            return self._infer_visualization_config(query, results)
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取JSON对象
        
        Args:
            text: 文本字符串
            
        Returns:
            提取的JSON对象，提取失败则返回空字典
        """
        if not text:
            return {}
            
        # 尝试直接解析整个字符串
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 尝试使用正则表达式提取JSON对象
        try:
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except (json.JSONDecodeError, re.error):
            pass
            
        # 尝试匹配带有```json标记的代码块
        try:
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_block_match:
                return json.loads(json_block_match.group(1))
        except (json.JSONDecodeError, re.error):
            pass
            
        # 所有尝试都失败，返回空字典
        return {}
        
    def _infer_visualization_config(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """
        根据查询和结果智能推断可视化配置
        
        Args:
            query: 查询文本
            results: 查询结果
            
        Returns:
            推断的可视化配置
        """
        # 默认配置
        config = {
            "chart_type": "table",
            "title": f"查询结果: {query}",
            "description": "系统根据查询结果自动推荐的可视化方式"
        }
        
        # 如果结果为空，返回默认配置
        if not results:
            return config
            
        # 检查results是否为嵌套列表
        if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
            logger.warning("结果是嵌套列表，使用第一个子列表")
            # 如果是嵌套列表，使用第一个子列表
            results = results[0]
            
        # 检查结果第一项是否为字典类型
        if not results or not isinstance(results[0], dict):
            logger.warning(f"无法识别的结果格式: {type(results)} / {type(results[0] if results else None)}")
            return config
            
        # 获取所有列名
        try:
            columns = list(results[0].keys())
        except (AttributeError, TypeError, IndexError) as e:
            logger.error(f"提取列名时出错: {str(e)}")
            return config
        
        # 聚合查询结果，通常是单行的汇总数据
        if len(results) == 1 and len(columns) <= 3:
            # 可能是单个指标，使用仪表盘或卡片
            config["chart_type"] = "card"
            config["title"] = f"{query}的结果"
            config["metrics"] = []
            
            for col, val in results[0].items():
                metric = {
                    "name": col,
                    "value": val
                }
                config["metrics"].append(metric)
                
            return config
            
        # 检查是否有日期/时间列，适合用折线图
        date_cols = [col for col in columns if any(term in col.lower() for term in ["date", "time", "year", "month", "day"])]
        if date_cols and len(results) > 1:
            # 找到可能的数值列
            num_cols = []
            for row in results[:5]:  # 检查前5行就足够了
                for col in columns:
                    if col not in date_cols:
                        try:
                            val = row[col]
                            if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).isdigit()):
                                num_cols.append(col)
                        except (ValueError, TypeError, KeyError):
                            pass
            
            # 如果有日期列和数值列，使用折线图
            if date_cols and num_cols:
                config["chart_type"] = "line"
                config["title"] = f"{query}趋势"
                config["x_axis"] = date_cols[0]  # 使用第一个日期列作为X轴
                config["y_axis"] = list(set(num_cols))[:3]  # 最多使用3个数值列作为Y轴
                return config
                
        # 检查是否适合饼图（通常是分类统计）
        if len(results) <= 10 and len(columns) == 2:
            # 一列可能是分类，一列可能是数值
            if any(isinstance(results[0][col], (int, float)) or 
                   (isinstance(results[0][col], str) and results[0][col].replace('.', '', 1).isdigit()) 
                   for col in columns):
                config["chart_type"] = "pie"
                config["title"] = f"{query}分布"
                # 识别分类列和数值列
                cat_col = columns[0]
                val_col = columns[1]
                if isinstance(results[0][columns[0]], (int, float)) or (isinstance(results[0][columns[0]], str) and results[0][columns[0]].replace('.', '', 1).isdigit()):
                    cat_col = columns[1]
                    val_col = columns[0]
                config["category"] = cat_col
                config["value"] = val_col
                return config
                
        # 检查是否适合柱状图（分类比较）
        if len(results) <= 20 and len(columns) >= 2:
            # 至少有一个可能是分类列，一个是数值列
            potential_cat_cols = []
            potential_num_cols = []
            
            for col in columns:
                # 抽样检查值类型
                values = [row[col] for row in results[:5] if col in row]
                if all(isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '', 1).isdigit()) for v in values if v is not None):
                    potential_num_cols.append(col)
                else:
                    potential_cat_cols.append(col)
                    
            if potential_cat_cols and potential_num_cols:
                config["chart_type"] = "bar"
                config["title"] = f"{query}对比"
                config["x_axis"] = potential_cat_cols[0]  # 使用第一个分类列作为X轴
                config["y_axis"] = potential_num_cols[0]  # 使用第一个数值列作为Y轴
                return config
                
        # 默认使用表格
        return config
    
    async def suggest_queries(self, query: str, sql: str, summary: str) -> List[str]:
        """
        生成后续查询建议 (已废弃，仅保留兼容性)
        
        Args:
            query: 原始自然语言查询
            sql: 执行的SQL查询
            summary: 结果摘要
            
        Returns:
            建议查询列表
        """
        # 直接调用新方法的第二个返回值
        _, suggestions = await self.generate_sql_with_suggestions(query)
        return suggestions
    
    def _clean_sql(self, sql_text: str) -> str:
        """
        清理和格式化SQL文本
        
        Args:
            sql_text: 原始SQL文本
            
        Returns:
            清理后的SQL
        """
        # 如果是空的，返回空字符串
        if not sql_text:
            return ""
            
        # 删除"```sql"和"```"标记
        sql_text = re.sub(r'```sql|```', '', sql_text)
        
        # 删除前导和尾随空白
        sql_text = sql_text.strip()
        
        # 如果文本中包含多个SQL语句，只取第一个
        if ";" in sql_text:
            statements = sql_text.split(";")
            # 取非空的第一个语句
            for stmt in statements:
                if stmt.strip():
                    sql_text = stmt.strip()
                    break
        
        return sql_text
    
    def _ensure_safe_sql(self, sql: str) -> str:
        """
        确保SQL是安全的和只读的
        
        Args:
            sql: 原始SQL
            
        Returns:
            安全的SQL
        """
        # 转换为大写以进行检查
        sql_upper = sql.upper()
        
        # 从配置中获取危险关键字列表，若无配置则使用默认值
        dangerous_keywords = settings.SQL_DANGEROUS_KEYWORDS if hasattr(settings, "SQL_DANGEROUS_KEYWORDS") else ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        
        # 定义SQL语句中的子句类型
        sql_clauses = ["SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT", "JOIN", "UNION", "WITH"]
        
        # 添加详细的调试日志
        logger.debug(f"检查SQL安全性: {sql}")
        logger.debug(f"配置的危险关键字: {dangerous_keywords}")
        
        # 检查是否包含非允许的操作
        for keyword in dangerous_keywords:
            # 先检查关键字是否作为独立命令存在
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.finditer(pattern, sql_upper)
            
            for match in matches:
                start_pos = match.start()
                
                # 检查该关键字是否在安全上下文中（作为列名、表名或子查询一部分）
                is_safe = False
                
                # 检查前面是否有安全子句
                for clause in sql_clauses:
                    clause_pos = sql_upper.rfind(clause, 0, start_pos)
                    if clause_pos != -1 and clause_pos < start_pos:
                        # 找到子句和关键字之间的文本
                        context_text = sql_upper[clause_pos:start_pos]
                        # 如果子句和关键字之间没有分号，认为是安全的
                        if ";" not in context_text:
                            is_safe = True
                            logger.debug(f"关键字 {keyword} 在安全上下文中: {clause} ... {keyword}")
                            break
                
                # 检查是否在引号内（列名或字符串值）
                if not is_safe:
                    # 计算到该位置的引号数量
                    quotes_before = sql[:start_pos].count('"') + sql[:start_pos].count("'")
                    if quotes_before % 2 == 1:  # 奇数表示在引号内
                        is_safe = True
                        logger.debug(f"关键字 {keyword} 在引号内，被视为安全")
                
                # 检查是否作为标识符部分（如列名带下划线）
                if not is_safe:
                    # 检查前一个字符是否是标识符的一部分
                    if start_pos > 0 and sql[start_pos-1].isalnum() or sql[start_pos-1] == '_':
                        is_safe = True
                        logger.debug(f"关键字 {keyword} 是标识符的一部分，被视为安全")
                
                # 如果不是安全上下文中的关键字，则拒绝查询
                if not is_safe:
                    logger.warning(f"SQL包含危险关键字: {keyword} 在位置 {start_pos}")
                    raise ValueError(f"不允许执行包含{keyword}的SQL（不在安全上下文中）")
            
        # 如果没有LIMIT，添加LIMIT 100
        if "LIMIT" not in sql_upper:
            limit_value = settings.SQL_AUTO_LIMIT if hasattr(settings, "SQL_AUTO_LIMIT") else 100
            if ";" in sql:
                sql = sql.replace(";", f" LIMIT {limit_value};")
            else:
                sql = f"{sql} LIMIT {limit_value}"
                
        logger.debug(f"SQL安全检查通过: {sql}")
        return sql
    
    def _format_results(self, results: List[Dict]) -> List[Dict]:
        """
        格式化结果以确保可以序列化为JSON
        
        Args:
            results: 原始结果
            
        Returns:
            格式化后的结果
        """
        formatted_results = []
        
        for row in results:
            formatted_row = {}
            
            for key, value in row.items():
                # 处理日期时间
                if isinstance(value, (datetime, timedelta)):
                    formatted_row[key] = str(value)
                # 处理其他不可JSON序列化的类型
                elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                    formatted_row[key] = str(value)
                else:
                    formatted_row[key] = value
                    
            formatted_results.append(formatted_row)
            
        return formatted_results
    
    async def _fallback_sql_generation(self, query: str) -> Tuple[str, List[str]]:
        """
        回退SQL生成方法，当LLM生成失败时使用
        
        Args:
            query: 自然语言查询
            
        Returns:
            (错误提示信息, 默认建议列表)元组
        """
        # 生成默认建议
        suggestions = self._generate_default_suggestions(query)
        
        # 直接返回错误提示和默认建议
        logger.error(f"LLM生成SQL失败，无法处理查询: {query}")
        return "__ERROR__: SQL生成失败，请重新描述您的查询或稍后再试", suggestions
    
    def _generate_default_suggestions(self, query: str) -> List[str]:
        """
        生成默认查询建议
        
        Args:
            query: 原始查询
            
        Returns:
            默认建议列表
        """
        default_suggestions = [
            "过去30天销量最高的产品是什么?",
            "哪些客户在过去一年中贡献了最多的收入?",
            "各产品类别的平均利润率是多少?",
            "退货率最高的产品有哪些共同特征?",
            "销售趋势如何随季节变化?"
        ]
        
        # 确保建议与当前查询不同
        return [s for s in default_suggestions if s.lower() != query.lower()][:3]
    
    async def explain_results_stream(self, query: str, sql: str, results: List[Dict]) -> AsyncGenerator[str, None]:
        """
        流式生成解释结果
        
        Args:
            query: 用户原始查询
            sql: 执行的SQL语句
            results: 查询结果
            
        Yields:
            生成的解释文本块
        """
        self.logger.info(f"开始流式生成查询解释...")
        
        # 准备给LLM的上下文
        result_str = ""
        if results and len(results) > 0:
            result_samples = results[:10]  # 限制样本数量
            if isinstance(result_samples[0], dict):
                result_str = "\n".join([json.dumps(row, ensure_ascii=False, default=str) for row in result_samples])
                if len(results) > 10:
                    result_str += f"\n... 共{len(results)}条结果"
            else:
                result_str = str(result_samples)
        else:
            result_str = "空结果集"
        
        # 构建提示
        prompt = f"""用户查询: "{query}"
执行的SQL: {sql}
查询结果 (最多显示10条): 
{result_str}

请解释这些查询结果，包含以下内容：
1. 结果的简要总结
2. 关键发现和见解
3. 重要的数据点分析
4. 与用户原始问题的关联性

格式要求:
- 使用Markdown格式
- 简洁明了
- 专业且信息丰富
- 重点突出关键数据和洞察
"""
        
        self.logger.info(f"流式解释查询提示构建完成，长度: {len(prompt)}")
        
        # 使用LLM生成解释 - 流式模式
        self.logger.info(f"开始流式生成解释...")
        
        try:
            # 确保我们的适配器支持流式输出
            if hasattr(self.llm_adapter, "generate_stream"):
                async for token in self.llm_adapter.generate_stream(prompt):
                    yield token
            else:
                # 如果不支持流式输出，使用模拟的流式输出
                full_response = await self.llm_adapter.generate(prompt)
                
                # 模拟流式输出 (单词级别)
                words = full_response.split(' ')
                for word in words:
                    yield word + ' '
                    await asyncio.sleep(0.05)  # 模拟延迟
                
            self.logger.info(f"流式解释生成完成")
            
        except Exception as e:
            self.logger.error(f"解释生成失败: {str(e)}")
            raise


def get_nl2sql_chain(
    include_tables: Optional[List[str]] = None,
    exclude_tables: Optional[List[str]] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    use_direct_connection: bool = False,
    proxy: Optional[Dict[str, str]] = None,
    top_k: int = 10,
    database_name: Optional[str] = None,
    config: Optional[Dict[str, bool]] = None
) -> NL2SQLChain:
    """
    获取自然语言转SQL的链
    
    Args:
        include_tables: 包含的表名列表
        exclude_tables: 排除的表名列表
        temperature: 模型温度参数
        max_tokens: 最大生成token数
        use_direct_connection: 是否使用直接连接
        proxy: 代理配置
        top_k: 查询中使用的top_k结果数
        database_name: 数据库名称
        config: 链配置
    
    Returns:
        NL2SQLChain实例
    """
    try:
        # 确定使用哪个AI模型
        model_type = settings.DEFAULT_AI_MODEL.lower()
        
        # 创建数据库工具包
        database_toolkit = DatabaseToolkit(include_tables=include_tables, exclude_tables=exclude_tables)
        
        # 创建NL2SQL链实例
        nl2sql_chain = NL2SQLChain(database_toolkit=database_toolkit, config=config)
        
        # 日志记录
        logger.info(f"成功创建NL2SQLChain，使用模型: {model_type}")
        
        return nl2sql_chain
    except Exception as e:
        logger.error(f"创建NL2SQLChain失败: {str(e)}")
        # 返回一个基本的NL2SQL链实例，没有LLM支持
        database_toolkit = DatabaseToolkit(include_tables=include_tables, exclude_tables=exclude_tables)
        return NL2SQLChain(database_toolkit=database_toolkit, config=config)