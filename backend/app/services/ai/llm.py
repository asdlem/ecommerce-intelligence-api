"""
LLM服务模块，提供大语言模型的API调用功能
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union
import httpx
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import traceback
import asyncio

from app.core.config import settings
from app.core.logging import get_logger

# 配置日志
logger = get_logger(__name__)


class LLMService:
    """大语言模型服务基类"""
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成文本响应（需要在子类中实现）
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的响应
        """
        raise NotImplementedError("子类必须实现generate方法")


class OpenRouterLLMService(LLMService):
    """OpenRouter LLM服务类
    
    使用OpenRouter API进行大语言模型访问，支持多种模型
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        use_sdk: bool = False,
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        timeout: float = 60.0
    ):
        """
        初始化OpenRouter LLM服务
        
        Args:
            api_key: OpenRouter API密钥，默认使用环境变量OPENROUTER_API_KEY
            api_base: API基础URL
            model: 模型名称
            use_sdk: 是否使用SDK
            http_referer: HTTP来源地址
            x_title: 标题
            proxy: 代理设置
            timeout: 超时时间(秒)
        """
        # 设置API密钥
        self.api_key = api_key or settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
        
        # 如果API密钥为空，记录警告但继续初始化
        if not self.api_key:
            logger.warning("没有提供OpenRouter API密钥，请在设置中配置OPENROUTER_API_KEY或设置环境变量")
        
        # 设置其他参数
        self.api_base = api_base or settings.OPENROUTER_API_BASE
        self.model = model or settings.OPENROUTER_MODEL
        self.http_referer = http_referer or settings.OPENROUTER_HTTP_REFERER
        self.x_title = x_title or settings.OPENROUTER_X_TITLE
        
        # 使用openai库时的通用参数
        self.use_sdk = use_sdk
        self.proxy = proxy
        self.timeout = timeout
        
        # 初始化OpenAI客户端
        self._client = None
        
        logger.info(f"初始化OpenRouter LLM服务: 模型={self.model}, API基础URL={self.api_base}")
    
    @property
    def client(self):
        """延迟加载的OpenAI客户端"""
        if self._client is None:
            try:
                # 动态导入OpenAI
                import openai
                
                # 设置OpenAI客户端配置
                self._client = openai.Client(
                    api_key=self.api_key,
                    base_url=self.api_base,
                    timeout=self.timeout
                )
                
                # 从settings或使用传入参数设置代理
                if not self.use_sdk:
                    # 设置代理
                    if self.proxy:
                        http_client = httpx.Client(proxies=self.proxy)
                        self._client._client = http_client
                    # 如果设置了环境变量HTTP_PROXY/HTTPS_PROXY，httpx会自动使用
                
                logger.debug("成功初始化OpenAI客户端")
            except ImportError:
                logger.error("无法导入openai库。请安装: pip install openai>=1.0.0")
                raise
            except Exception as e:
                logger.error(f"初始化OpenAI客户端时出错: {str(e)}")
                raise
                
        return self._client
    
    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        headers = {}
        
        # 添加引用信息
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
            
        # 添加标题
        if self.x_title:
            headers["X-Title"] = self.x_title
            
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, httpx.HTTPError))
    )
    async def generate(
        self, 
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成文本响应
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的响应
        """
        start_time = time.time()
        
        try:
            # 记录请求细节，用于调试
            logger.debug(f"发送请求到OpenRouter, 模型: {self.model}")
            logger.debug(f"消息数量: {len(messages)}")
            
            # 使用OpenAI客户端发送请求
            if not max_tokens:
                max_tokens = 2048  # 默认值
                
            # 准备OpenAI客户端调用参数
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "extra_headers": self._prepare_headers()  # 添加自定义头部
            }
            
            # 调用OpenAI API
            response = await self.client.chat.completions.create(**params)
            
            # 将响应转换为字典
            response_dict = {
                "id": response.id,
                "model": response.model,
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            # 记录响应时间和token使用情况
            elapsed_time = time.time() - start_time
            tokens = response_dict.get("usage", {})
            
            log_llm_request(
                prompt=str(messages),
                response=response_dict.get("choices", [{}])[0].get("message", {}).get("content", ""),
                model=self.model,
                tokens=tokens,
                time=elapsed_time
            )
            
            return response_dict
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"OpenRouter生成请求失败: {error_msg}, 耗时: {elapsed_time:.2f}秒")
            
            # 返回错误响应
            return {
                "id": "error",
                "error": True,
                "message": error_msg,
                "choices": [
                    {
                    "message": {
                        "role": "assistant",
                            "content": f"抱歉，模型服务出现错误: {error_msg}"
                        },
                        "finish_reason": "error"
                    }
                ]
            }


class DeepSeekLLMService(LLMService):
    """DeepSeek LLM服务类
    
    使用DeepSeek API进行大语言模型访问，通过OpenAI SDK接口
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        use_sdk: bool = False,
        proxy: Optional[Dict[str, str]] = None,
        timeout: float = 60.0
    ):
        """
        初始化DeepSeek LLM服务
        
        Args:
            api_key: DeepSeek API密钥
            api_base: API基础URL
            model: 模型名称
            use_sdk: 是否使用SDK
            proxy: 代理设置
            timeout: 超时时间(秒)
        """
        # 设置API密钥
        self.api_key = api_key or settings.DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
        
        # 如果API密钥为空，记录警告但继续初始化
        if not self.api_key:
            logger.warning("没有提供DeepSeek API密钥，请在设置中配置DEEPSEEK_API_KEY或设置环境变量")
        
        # 设置其他参数
        self.api_base = api_base or settings.DEEPSEEK_API_BASE
        self.model = model or settings.DEEPSEEK_MODEL
        
        # 使用openai库时的通用参数
        self.use_sdk = use_sdk
        self.proxy = proxy
        self.timeout = timeout
        
        # 初始化OpenAI客户端
        self._client = None
        
        logger.info(f"初始化DeepSeek LLM服务: 模型={self.model}, API基础URL={self.api_base}")
    
    @property
    def client(self):
        """延迟加载的OpenAI客户端"""
        if self._client is None:
            try:
                # 动态导入OpenAI
                import openai
                
                # 设置OpenAI客户端配置
                self._client = openai.Client(
                    api_key=self.api_key,
                    base_url=self.api_base,
                timeout=self.timeout
            )
            
                # 从settings或使用传入参数设置代理
                if not self.use_sdk:
                    # 设置代理
                    if self.proxy:
                        http_client = httpx.Client(proxies=self.proxy)
                        self._client._client = http_client
                    # 如果设置了环境变量HTTP_PROXY/HTTPS_PROXY，httpx会自动使用
                
                logger.debug("成功初始化DeepSeek的OpenAI客户端")
            except ImportError:
                logger.error("无法导入openai库。请安装: pip install openai>=1.0.0")
                raise
            except Exception as e:
                logger.error(f"初始化DeepSeek的OpenAI客户端时出错: {str(e)}")
                raise
                
        return self._client
    
    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        headers = {}
        
        # 添加引用信息
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
            
        # 添加标题
        if self.x_title:
            headers["X-Title"] = self.x_title
            
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, httpx.HTTPError))
    )
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7, 
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成文本响应
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的响应
        """
        start_time = time.time()
        
        try:
            # 记录请求细节，用于调试
            logger.debug(f"发送请求到DeepSeek, 模型: {self.model}")
            logger.debug(f"消息数量: {len(messages)}")
            
            # 使用OpenAI客户端发送请求
            if not max_tokens:
                max_tokens = 2048  # 默认值
                
            # 准备OpenAI客户端调用参数
            params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
                "max_tokens": max_tokens,
                "extra_headers": self._prepare_headers()  # 添加自定义头部
            }
            
            # 调用OpenAI API
            response = await self.client.chat.completions.create(**params)
            
            # 将响应转换为字典
            response_dict = {
                "id": response.id,
                "model": response.model,
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            # 记录响应时间和token使用情况
            elapsed_time = time.time() - start_time
            tokens = response_dict.get("usage", {})
            
            log_llm_request(
                prompt=str(messages),
                response=response_dict.get("choices", [{}])[0].get("message", {}).get("content", ""),
                model=self.model,
                tokens=tokens,
                time=elapsed_time
            )
            
            return response_dict
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"DeepSeek生成请求失败: {error_msg}, 耗时: {elapsed_time:.2f}秒")
            
            # 返回错误响应
            return {
                "id": "error",
                "error": True,
                "message": error_msg,
                "choices": [
                    {
                    "message": {
                        "role": "assistant",
                            "content": f"抱歉，模型服务出现错误: {error_msg}"
                        },
                        "finish_reason": "error"
                    }
                ]
            }


def get_llm_service(
    provider: str = None,
    api_key: str = None,
    model: str = None,
    use_direct_connection: bool = False,
    proxy: Optional[Dict[str, str]] = None,
    use_sdk: bool = False
) -> Union[OpenRouterLLMService, DeepSeekLLMService]:
    """获取LLM服务实例
    
    Args:
        provider: 提供商名称，可以是"openrouter"或"deepseek"
        api_key: API密钥
        model: 模型名称
        use_direct_connection: 是否使用直接连接
        proxy: 代理设置
        use_sdk: 是否使用SDK
    
    Returns:
        LLM服务实例
    """
    # 如果未指定提供商，使用配置中的默认值
    if not provider:
        provider = settings.DEFAULT_AI_MODEL.lower()
    
    # 根据提供商创建相应的服务
    if provider.lower() == "openrouter":
            return OpenRouterLLMService(
            api_key=api_key,
            model=model,
            use_sdk=use_sdk,
            proxy=proxy if use_direct_connection else None
            )
    else:
        # 默认使用DeepSeek
        return DeepSeekLLMService(
            api_key=api_key,
            model=model,
            use_sdk=use_sdk,
            proxy=proxy if use_direct_connection else None
            )


# 详细日志记录函数
def log_llm_request(prompt, response, model, tokens=None, time=None):
    """
    记录LLM请求的详细信息
    
    Args:
        prompt: 发送给LLM的提示词
        response: LLM的响应内容
        model: 使用的LLM模型名称
        tokens: 使用的token数量
        time: 请求耗时(秒)
    """
    logger.debug("----- LLM请求详情 -----")
    logger.debug(f"模型: {model}")
    
    # 记录提示词
    if isinstance(prompt, str):
        logger.debug(f"提示词: {prompt[:1000]}..." if len(prompt) > 1000 else f"提示词: {prompt}")
    else:
        logger.debug(f"提示词: {str(prompt)[:1000]}...")
    
    # 记录响应内容
    if isinstance(response, str):
        logger.debug(f"响应内容: {response[:1000]}..." if len(response) > 1000 else f"响应内容: {response}")
    else:
        logger.debug(f"响应内容: {str(response)[:1000]}...")
    
    if tokens:
        logger.debug(f"Token使用: {tokens}")
    if time:
        logger.debug(f"请求耗时: {time:.2f}秒")
    logger.debug("--------------------------") 