from typing import List, Optional, Union, Dict, Any
import json
import os
import secrets
from pathlib import Path
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
import logging
import re

# 设置基本日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("config")

# 获取配置文件路径
CONFIG_PATH = Path(__file__).parents[2] / "config.json"
logger.info(f"配置文件路径: {CONFIG_PATH}")

def get_project_root() -> Path:
    """获取项目根目录"""
    # 假设config.py文件在backend/app/core目录下
    return Path(__file__).parent.parent.parent.absolute()

def load_config() -> Dict[str, Any]:
    """
    加载配置文件并替换环境变量占位符
    
    配置文件中的占位符格式为 ${ENV_VAR_NAME}
    """
    config_path = os.path.join(get_project_root(), "config.json")
    
    # 读取配置文件
    with open(config_path, "r", encoding="utf-8") as f:
        config_str = f.read()
    
    # 替换环境变量占位符
    pattern = r"\${([A-Za-z0-9_]+)}"
    
    def replace_env_var(match):
        env_var_name = match.group(1)
        env_value = os.environ.get(env_var_name)
        if env_value is None:
            print(f"警告: 环境变量 {env_var_name} 未设置，使用空字符串替代")
            return ""
        return env_value
    
    # 使用正则表达式替换所有环境变量占位符
    config_str = re.sub(pattern, replace_env_var, config_str)
    
    # 解析JSON配置
    try:
        return json.loads(config_str)
    except json.JSONDecodeError as e:
        print(f"配置文件解析错误: {e}")
        raise

# 加载配置
config_data = load_config()

class Settings(BaseSettings):
    """应用配置设置"""
    # 基础设置
    PROJECT_NAME: str = config_data.get("project", {}).get("name", "ECommerceEfficiencyAgent")
    PROJECT_DESCRIPTION: str = config_data.get("project", {}).get("description", "通过AI能力为电商场景提供智能化功能的效率提升工具")
    VERSION: str = config_data.get("project", {}).get("version", "0.1.0")
    API_V1_STR: str = config_data.get("project", {}).get("api_v1_str", "/api/v1")
    
    # 测试模式设置
    TEST_MODE: bool = False
    TEST_USER_ID: int = 1
    
    # CORS设置
    CORS_ORIGINS: List[str] = config_data.get("cors", {}).get("origins", ["*"])

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 数据库设置 - 从环境变量优先读取
    DATABASE_TYPE: str = os.environ.get("DB_TYPE") or config_data.get("database", {}).get("type", "mysql")
    MYSQL_HOST: str = os.environ.get("DB_HOST") or config_data.get("database", {}).get("host", "localhost")
    MYSQL_PORT: int = int(os.environ.get("DB_PORT") or config_data.get("database", {}).get("port", 3306))
    MYSQL_USER: str = os.environ.get("DB_USER") or config_data.get("database", {}).get("user", "agent_user")
    MYSQL_PASSWORD: str = os.environ.get("DB_PASSWORD") or config_data.get("database", {}).get("password", "agent_password")
    MYSQL_DB: str = os.environ.get("DB_NAME") or config_data.get("database", {}).get("db", "agent_db")
    SQLITE_PATH: str = os.environ.get("SQLITE_PATH") or config_data.get("database", {}).get("sqlite_path", "test.db")
    
    # 数据库连接URL - 现在作为常规字段
    DATABASE_URL: str = ""
    SYNC_DATABASE_URL: str = ""
    
    DATABASE_ECHO: bool = config_data.get("database", {}).get("echo", False)
    
    # JWT认证设置
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config_data.get("jwt", {}).get("access_token_expire_minutes", 60 * 24 * 8)  # 默认8天
    
    # AI模型设置
    DEFAULT_AI_MODEL: str = config_data.get("ai_models", {}).get("default_ai_model", "deepseek")
    
    # 推理功能设置
    ENABLE_REASONING: bool = config_data.get("ai_models", {}).get("enable_reasoning", True)
    
    # OpenRouter设置
    OPENROUTER_API_KEY: str = config_data.get("ai_models", {}).get("openrouter", {}).get("api_key", "")
    OPENROUTER_API_BASE: str = config_data.get("ai_models", {}).get("openrouter", {}).get("api_base", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL: str = config_data.get("ai_models", {}).get("openrouter", {}).get("model", "deepseek/deepseek-chat-v3-0324:free")
    OPENROUTER_HTTP_REFERER: str = config_data.get("ai_models", {}).get("openrouter", {}).get("http_referer", "https://agent.example.com")
    OPENROUTER_X_TITLE: str = config_data.get("ai_models", {}).get("openrouter", {}).get("x_title", "ECommerceEfficiencyAgent")
    
    # DeepSeek设置
    DEEPSEEK_API_KEY: str = config_data.get("ai_models", {}).get("deepseek", {}).get("api_key", "")
    DEEPSEEK_API_BASE: str = config_data.get("ai_models", {}).get("deepseek", {}).get("api_base", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = config_data.get("ai_models", {}).get("deepseek", {}).get("model", "deepseek-chat")
    DEEPSEEK_HTTP_REFERER: str = config_data.get("ai_models", {}).get("deepseek", {}).get("http_referer", "https://agent.example.com")
    DEEPSEEK_X_TITLE: str = config_data.get("ai_models", {}).get("deepseek", {}).get("x_title", "ECommerceEfficiencyAgent")
    
    # 嵌入模型设置
    EMBEDDING_PROVIDER: str = config_data.get("embedding", {}).get("provider", "siliconflow") 
    EMBEDDING_API_KEY: str = config_data.get("embedding", {}).get("api_key", "")
    EMBEDDING_API_BASE: str = config_data.get("embedding", {}).get("api_base", "https://api.siliconflow.cn/v1/embeddings")
    EMBEDDING_MODEL: str = config_data.get("embedding", {}).get("model", "BAAI/bge-m3")
    EMBEDDING_DIMENSION: int = config_data.get("embedding", {}).get("dimension", 1024)
    
    # 重排序模型设置
    RERANKER_PROVIDER: str = config_data.get("reranker", {}).get("provider", "siliconflow")
    RERANKER_API_KEY: str = config_data.get("reranker", {}).get("api_key", "")
    RERANKER_API_BASE: str = config_data.get("reranker", {}).get("api_base", "https://api.siliconflow.cn/v1/rerank")
    RERANKER_MODEL: str = config_data.get("reranker", {}).get("model", "BAAI/bge-reranker-v2-m3")
    
    # 向量数据库设置
    VECTOR_STORE_TYPE: str = config_data.get("vector_store", {}).get("type", "chroma")
    VECTOR_STORE_URL: Optional[str] = config_data.get("vector_store", {}).get("url", None)
    VECTOR_STORE_API_KEY: Optional[str] = config_data.get("vector_store", {}).get("api_key", None)
    VECTOR_COLLECTION_NAME: str = config_data.get("vector_store", {}).get("collection_name", "ecommerce_knowledge")
    
    # 日志配置
    LOG_LEVEL: str = config_data.get("logging", {}).get("level", "INFO")
    
    # SQL安全配置
    SQL_DANGEROUS_KEYWORDS: List[str] = config_data.get("sql_security", {}).get("dangerous_keywords", 
        ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"])
    SQL_ENFORCE_READ_ONLY: bool = config_data.get("sql_security", {}).get("enforce_read_only", True)
    SQL_AUTO_LIMIT: int = config_data.get("sql_security", {}).get("auto_limit", 100)
    
    # 管理员初始密码
    INITIAL_ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD") or config_data.get("admin", {}).get("initial_admin_password", "admin123")
    
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 处理测试模式环境变量
        test_mode_env = os.environ.get("TEST_MODE", "").lower()
        if test_mode_env in ["true", "1", "yes"]:
            self.TEST_MODE = True
            logger.info("已启用测试模式")
        elif test_mode_env in ["false", "0", "no"]:
            self.TEST_MODE = False
        
        # 处理环境变量覆盖配置
        # OpenRouter API密钥
        env_openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        if env_openrouter_api_key:
            self.OPENROUTER_API_KEY = env_openrouter_api_key
            logger.info("使用环境变量中的OpenRouter API密钥")
            
        # DeepSeek API密钥
        env_deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        if env_deepseek_api_key:
            self.DEEPSEEK_API_KEY = env_deepseek_api_key
            logger.info("使用环境变量中的DeepSeek API密钥")
            
        # DEFAULT_AI_MODEL
        env_default_ai_model = os.environ.get("DEFAULT_AI_MODEL")
        if env_default_ai_model and env_default_ai_model.lower() in ["openrouter", "deepseek"]:
            self.DEFAULT_AI_MODEL = env_default_ai_model.lower()
            logger.info(f"使用环境变量中的默认AI模型: {self.DEFAULT_AI_MODEL}")
            
        # 根据数据库类型构建数据库连接URL
        if self.DATABASE_TYPE.lower() == "sqlite":
            sqlite_path = Path(__file__).parents[2] / self.SQLITE_PATH
            self.DATABASE_URL = f"sqlite+aiosqlite:///{sqlite_path}"
            self.SYNC_DATABASE_URL = f"sqlite:///{sqlite_path}"
            logger.info(f"使用SQLite数据库: {sqlite_path}")
        else:
            self.DATABASE_URL = f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            self.SYNC_DATABASE_URL = f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            logger.info(f"使用MySQL数据库: {self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}")
        
        # 记录关键配置信息
        logger.info(f"AI模型配置: 默认模型={self.DEFAULT_AI_MODEL}")
        if not self.OPENROUTER_API_KEY and self.DEFAULT_AI_MODEL == "openrouter":
            logger.warning("警告: 使用OpenRouter作为默认模型，但未设置API密钥")
        if not self.DEEPSEEK_API_KEY and self.DEFAULT_AI_MODEL == "deepseek":
            logger.warning("警告: 使用DeepSeek作为默认模型，但未设置API密钥")

# 创建全局设置实例
try:
    settings = Settings() 
    logger.info("成功初始化配置")
except Exception as e:
    logger.critical(f"初始化配置失败: {e}")
    raise 