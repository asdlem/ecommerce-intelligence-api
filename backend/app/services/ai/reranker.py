"""重排序服务模块

提供文本重排序服务，用于对检索结果进行精确排序。
"""

import logging
import os
from typing import List, Dict, Any, Tuple, Optional
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class RerankerService:
    """重排序服务类"""
    
    def __init__(
        self,
        api_key: str = settings.RERANKER_API_KEY,
        api_base: str = settings.RERANKER_API_BASE,
        model: str = settings.RERANKER_MODEL,
        use_direct_connection: bool = False,
        proxy: Optional[Dict[str, str]] = None
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.use_direct_connection = use_direct_connection
        self.proxy = proxy
        
        if not self.api_key:
            logger.warning("SiliconFlow API Key未设置，重排序服务可能无法正常工作")
    
    async def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_n: Optional[int] = None
    ) -> List[Tuple[int, float, str]]:
        """
        对文档列表进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_n: 返回的结果数量，None表示返回全部
            
        Returns:
            排序后的结果列表，每个元素为(原索引, 相关度分数, 文档内容)
        """
        if not documents:
            return []
        
        if top_n is None or top_n > len(documents):
            top_n = len(documents)
        
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
        
        try:
            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
                "return_documents": True
            }
            
            logger.info(f"发送重排序请求至 {self.api_base}, 模型: {self.model}")
            logger.debug(f"代理设置: {proxies}")
            
            response = requests.post(
                self.api_base,
                headers=headers,
                json=payload,
                proxies=proxies,
                timeout=30  # 添加超时设置
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 构造结果
            reranked_results = []
            for item in result.get("results", []):
                idx = item.get("index", 0)
                score = item.get("relevance_score", 0.0)
                doc_text = item.get("document", {}).get("text", documents[idx])
                reranked_results.append((idx, score, doc_text))
            
            return reranked_results
        
        except Exception as e:
            logger.error(f"重排序请求失败: {str(e)}")
            if isinstance(e, requests.RequestException) and hasattr(e, 'response') and e.response:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
            # 发生错误时返回原始顺序
            return [(i, 0.0, doc) for i, doc in enumerate(documents[:top_n])]


def get_reranker_service(
    use_direct_connection: bool = False,
    proxy: Optional[Dict[str, str]] = None
) -> RerankerService:
    """
    获取重排序服务实例
    
    Args:
        use_direct_connection: 是否使用直接连接（忽略代理）
        proxy: 自定义代理设置，如 {"http": "http://proxy:port", "https": "https://proxy:port"}
    
    Returns:
        RerankerService实例
    """
    return RerankerService(
        use_direct_connection=use_direct_connection,
        proxy=proxy
    ) 