"""嵌入服务模块

提供文本嵌入服务，支持不同的嵌入模型提供商。
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Union, Optional, Dict, Any

import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    """嵌入服务基类"""
    
    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        获取文本嵌入向量
        
        Args:
            texts: 要嵌入的文本列表
            
        Returns:
            嵌入向量列表
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """获取嵌入向量维度"""
        pass


class SiliconFlowEmbeddingService(EmbeddingService):
    """硅基流动嵌入服务"""
    
    def __init__(
        self,
        api_key: str = settings.EMBEDDING_API_KEY,
        api_base: str = settings.EMBEDDING_API_BASE,
        model: str = settings.EMBEDDING_MODEL,
        dimension: int = settings.EMBEDDING_DIMENSION,
        use_direct_connection: bool = False,
        proxy: Optional[Dict[str, str]] = None
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self._dimension = dimension
        self.use_direct_connection = use_direct_connection
        self.proxy = proxy
        
        if not self.api_key:
            logger.warning("SiliconFlow API Key未设置，嵌入服务可能无法正常工作")
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        从硅基流动API获取嵌入向量
        
        Args:
            texts: 要嵌入的文本列表
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 设置代理
        proxies = self.proxy
        
        # 如果设置了直接连接，则忽略系统代理
        if self.use_direct_connection:
            logger.info("使用直接连接模式，忽略系统代理")
            proxies = {
                "http": None,
                "https": None
            }
        # 如果没有设置直接连接也没有设置自定义代理，则使用系统代理（如果有）
        elif not proxies:
            if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
                logger.info("检测到系统代理设置，使用系统代理")
                # 让requests自动使用系统代理
                proxies = None
            else:
                logger.info("未检测到系统代理，使用直接连接")
                proxies = {
                    "http": None,
                    "https": None
                }
        
        all_embeddings = []
        
        # 每个文本单独请求嵌入
        for text in texts:
            try:
                payload = {
                    "model": self.model,
                    "input": text,
                    "encoding_format": "float"
                }
                
                logger.info(f"发送嵌入请求至 {self.api_base}, 模型: {self.model}")
                logger.debug(f"代理设置: {proxies}")
                
                response = requests.post(
                    self.api_base,
                    headers=headers,
                    json=payload,
                    proxies=proxies,
                    timeout=30  # 超时设置
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"嵌入请求成功，获取到响应")
                
                # 提取嵌入向量
                embedding = result["data"][0]["embedding"]
                all_embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"获取嵌入失败: {str(e)}")
                if isinstance(e, requests.RequestException) and hasattr(e, 'response') and e.response:
                    logger.error(f"响应状态码: {e.response.status_code}")
                    logger.error(f"响应内容: {e.response.text}")
                
                # 如果失败，返回一个全零向量
                all_embeddings.append([0.0] * self.dimension)
        
        return all_embeddings


def get_embedding_service(
    use_direct_connection: bool = False,
    proxy: Optional[Dict[str, str]] = None
) -> EmbeddingService:
    """
    根据配置获取嵌入服务实例
    
    Args:
        use_direct_connection: 是否使用直接连接（忽略代理）
        proxy: 自定义代理设置，如 {"http": "http://proxy:port", "https": "https://proxy:port"}
    
    Returns:
        EmbeddingService实例
    """
    provider = settings.EMBEDDING_PROVIDER.lower()
    
    if provider == "siliconflow":
        return SiliconFlowEmbeddingService(
            use_direct_connection=use_direct_connection,
            proxy=proxy
        )
    else:
        logger.warning(f"未知的嵌入提供商: {provider}，使用SiliconFlow作为默认")
        return SiliconFlowEmbeddingService(
            use_direct_connection=use_direct_connection,
            proxy=proxy
        ) 