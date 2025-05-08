"""LangChain适配器模块

将现有的LLM服务适配到LangChain框架。
"""

import logging
import asyncio
from typing import Any, Dict, List, Mapping, Optional, Iterator, Union, cast, Callable, AsyncGenerator
import os
import time
import httpx
import requests
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_community.chat_models import ChatOpenAI
from pydantic import Field, SecretStr

from app.services.ai.llm import OpenRouterLLMService, get_llm_service, log_llm_request
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def sync_validate_api_key(api_key: str, provider: str = "deepseek") -> bool:
    """同步方式验证API密钥
    
    Args:
        api_key: API密钥
        provider: 提供商，可以是"deepseek"或"openrouter"
        
    Returns:
        验证结果，True表示有效，False表示无效
    """
    try:
        if provider.lower() == "deepseek":
            # 使用简单的模型列表请求验证DeepSeek API
            response = requests.get(
                "https://api.deepseek.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
        else:  # openrouter
            # 使用模型列表端点验证OpenRouter API
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            
        # 记录响应，便于调试
        logger.debug(f"{provider.capitalize()} API密钥验证状态码: {response.status_code}")
        
        # 检查响应是否成功
        if response.status_code == 200:
            logger.info(f"{provider.capitalize()} API密钥验证成功")
            return True
        
        logger.warning(f"{provider.capitalize()} API密钥验证失败: {response.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"验证{provider.capitalize()} API密钥时出错: {str(e)}")
        return False

class ChatOpenRouter(ChatOpenAI):
    """专门为OpenRouter API设计的ChatOpenAI子类
    
    使用OpenRouter的API兼容OpenAI的接口
    """
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        validate_api_key: bool = True,  # 是否验证API密钥
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
        **kwargs
    ):
        """初始化OpenRouter聊天模型
        
        Args:
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            api_key: OpenRouter API密钥
            validate_api_key: 是否验证API密钥
            http_referer: HTTP来源地址，用于OpenRouter统计
            x_title: 应用标题，用于OpenRouter统计
        """
        # 获取API密钥
        openrouter_api_key = api_key or settings.OPENROUTER_API_KEY
        if not openrouter_api_key:
            logger.error("未提供OpenRouter API密钥")
            raise ValueError("未提供OpenRouter API密钥")
        
        # 如果开启了验证，则在初始化时使用同步方法验证API密钥
        if validate_api_key:
            try:
                # 使用同步验证方法，避免异步事件循环问题
                key_valid = sync_validate_api_key(openrouter_api_key, "openrouter")
                
                if not key_valid:
                    logger.warning(f"OpenRouter API密钥验证失败，但仍将继续初始化")
            except Exception as e:
                logger.error(f"验证OpenRouter API密钥时出错: {str(e)}")
                # 继续初始化，因为密钥可能在某些情况下仍然有效
        
        # 设置基本参数
        model_name = model_name or settings.OPENROUTER_MODEL
        
        # 获取HTTP引用和标题
        self.http_referer = http_referer or settings.OPENROUTER_HTTP_REFERER
        self.x_title = x_title or settings.OPENROUTER_X_TITLE
        
        logger.info(f"初始化OpenRouter连接，模型: {model_name}")
        
        # 初始化基类，设置OpenRouter的API基础URL
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=openrouter_api_key,
            base_url=settings.OPENROUTER_API_BASE,
            **kwargs
        )
        
        logger.info(f"初始化ChatOpenRouter成功，使用模型: {model_name}")
    
    def _prepare_request_headers(self) -> Dict[str, str]:
        """准备请求头，添加OpenRouter特定的头部"""
        headers = {}
        
        # 添加引用信息
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
            
        # 添加标题
        if self.x_title:
            headers["X-Title"] = self.x_title
            
        return headers
    
    async def _acreate(
        self,
        messages: List[Dict[str, Any]],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> dict:
        """重写_acreate方法，添加OpenRouter特定的头部和参数
        
        Args:
            messages: 消息列表
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            API响应字典
        """
        try:
            # 添加OpenRouter特定的头部
            headers = self._prepare_request_headers()
            if headers and "extra_headers" not in kwargs:
                kwargs["extra_headers"] = headers
            elif headers and "extra_headers" in kwargs:
                kwargs["extra_headers"].update(headers)
            
            # 添加OpenRouter特定的参数，如include_reasoning
            if "extra_body" not in kwargs:
                kwargs["extra_body"] = {}
            
            # 如果启用了推理功能，添加include_reasoning参数
            if settings.ENABLE_REASONING:
                kwargs["extra_body"]["include_reasoning"] = True
            
            # 调用父类的方法发送请求
            response = await super()._acreate(messages, stop, **kwargs)
            
            # 检查并记录响应
            logger.debug(f"OpenRouter API 原始响应: {response}")
            
            # 确保响应具有正确的格式
            if not isinstance(response, dict):
                logger.warning(f"OpenRouter返回了非字典响应: {type(response)}")
                # 创建一个最小化的有效响应
                return {
                    "id": "mock_id",
                    "choices": [
                        {
                            "message": {
                                "content": "API返回了非预期的响应格式，无法处理。请稍后再试。"
                            },
                            "finish_reason": "error"
                        }
                    ],
                    "usage": {"total_tokens": 0},
                    "model": self.model_name
                }
                
            # 检查必要的字段
            if "choices" not in response or not isinstance(response["choices"], list):
                logger.warning("OpenRouter响应缺少choices字段或格式不正确")
                response["choices"] = [
                    {
                        "message": {
                            "content": "API响应缺少必要的choices字段，无法提取结果。"
                        },
                        "finish_reason": "error"
                    }
                ]
            
            # 确保choices非空
            if not response["choices"]:
                logger.warning("OpenRouter返回空choices列表")
                response["choices"] = [
                    {
                        "message": {
                            "content": "API未返回任何生成内容。"
                        },
                        "finish_reason": "error"
                    }
                ]
                
            # 检查并修复第一个choice
            first_choice = response["choices"][0]
            if not isinstance(first_choice, dict):
                logger.warning(f"OpenRouter choice不是字典: {type(first_choice)}")
                response["choices"][0] = {
                    "message": {
                        "content": "API响应格式异常，无法提取生成内容。"
                    },
                    "finish_reason": "error"
                }
                
            # 检查并修复message字段
            if "message" not in first_choice or not isinstance(first_choice["message"], dict):
                logger.warning("OpenRouter响应缺少message字段或格式不正确")
                response["choices"][0]["message"] = {
                    "content": "API响应缺少必要的message字段，无法提取结果。"
                }
                
            # 检查并修复content字段  
            if "content" not in first_choice.get("message", {}):
                logger.warning("OpenRouter响应message缺少content字段")
                response["choices"][0]["message"]["content"] = "API响应缺少必要的content字段，无法提取结果。"
                
            # 额外处理reasoning字段
            if settings.ENABLE_REASONING and "reasoning" in first_choice.get("message", {}):
                # 记录推理过程
                reasoning = first_choice["message"].get("reasoning", "")
                logger.debug(f"OpenRouter推理内容: {reasoning[:500]}...")
                
                # 可以根据需要对推理内容进行额外处理
                
            return response
            
        except Exception as e:
            logger.error(f"OpenRouter API请求失败: {str(e)}")
            # 返回一个模拟响应以避免崩溃
            return {
                "id": "error_id",
                "choices": [
                    {
                        "message": {
                            "content": f"API请求失败: {str(e)}"
                        },
                        "finish_reason": "error"
                    }
                ],
                "usage": {"total_tokens": 0},
                "model": self.model_name
            }

class ChatDeepSeek(ChatOpenAI):
    """专门为DeepSeek API设计的ChatOpenAI子类
    
    使用DeepSeek的API兼容OpenAI的接口
    """
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        validate_api_key: bool = True,  # 是否验证API密钥
        **kwargs
    ):
        """初始化DeepSeek聊天模型
        
        Args:
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            api_key: DeepSeek API密钥
            validate_api_key: 是否验证API密钥
        """
        # 获取API密钥
        deepseek_api_key = api_key or settings.DEEPSEEK_API_KEY
        if not deepseek_api_key:
            logger.error("未提供DeepSeek API密钥")
            raise ValueError("未提供DeepSeek API密钥")
        
        # 如果开启了验证，则在初始化时使用同步方法验证API密钥
        if validate_api_key:
            try:
                # 使用同步验证方法，避免异步事件循环问题
                key_valid = sync_validate_api_key(deepseek_api_key, "deepseek")
                
                if not key_valid:
                    logger.warning(f"DeepSeek API密钥验证失败，但仍将继续初始化")
            except Exception as e:
                logger.error(f"验证DeepSeek API密钥时出错: {str(e)}")
                # 继续初始化，因为密钥可能在某些情况下仍然有效
        
        # 设置基本参数
        model_name = model_name or settings.DEEPSEEK_MODEL
        
        logger.info(f"初始化DeepSeek连接，模型: {model_name}")
        
        # 初始化基类，设置DeepSeek的API基础URL
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=deepseek_api_key,
            base_url=settings.DEEPSEEK_API_BASE,
            **kwargs
        )
        
        logger.info(f"初始化ChatDeepSeek成功，使用模型: {model_name}")
    
    async def _acreate(
        self,
        messages: List[Dict[str, Any]],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> dict:
        """重写_acreate方法，增加错误处理和响应检查
        
        Args:
            messages: 消息列表
            stop: 停止词列表
            **kwargs: 其他参数
            
        Returns:
            API响应字典
        """
        try:
            # 调用父类的方法发送请求
            response = await super()._acreate(messages, stop, **kwargs)
            
            # 检查并记录响应
            logger.debug(f"DeepSeek API 原始响应: {response}")
            
            # 确保响应具有正确的格式
            if not isinstance(response, dict):
                logger.warning(f"DeepSeek返回了非字典响应: {type(response)}")
                # 创建一个最小化的有效响应
                return {
                    "id": "mock_id",
                    "choices": [
                        {
                            "message": {
                                "content": "API返回了非预期的响应格式，无法处理。请稍后再试。"
                            },
                            "finish_reason": "error"
                        }
                    ],
                    "usage": {"total_tokens": 0},
                    "model": self.model_name
                }
                
            # 检查必要的字段
            if "choices" not in response or not isinstance(response["choices"], list):
                logger.warning("DeepSeek响应缺少choices字段或格式不正确")
                response["choices"] = [
                    {
                        "message": {
                            "content": "API响应缺少必要的choices字段，无法提取结果。"
                        },
                        "finish_reason": "error"
                    }
                ]
            
            # 确保choices非空
            if not response["choices"]:
                logger.warning("DeepSeek返回空choices列表")
                response["choices"] = [
                    {
                        "message": {
                            "content": "API未返回任何生成内容。"
                        },
                        "finish_reason": "error"
                    }
                ]
                
            # 检查并修复第一个choice
            first_choice = response["choices"][0]
            if not isinstance(first_choice, dict):
                logger.warning(f"DeepSeek choice不是字典: {type(first_choice)}")
                response["choices"][0] = {
                    "message": {
                        "content": "API响应格式异常，无法提取生成内容。"
                    },
                    "finish_reason": "error"
                }
                
            # 检查并修复message字段
            if "message" not in first_choice or not isinstance(first_choice["message"], dict):
                logger.warning("DeepSeek响应缺少message字段或格式不正确")
                response["choices"][0]["message"] = {
                    "content": "API响应缺少必要的message字段，无法提取结果。"
                }
                
            # 检查并修复content字段  
            if "content" not in first_choice.get("message", {}):
                logger.warning("DeepSeek响应message缺少content字段")
                response["choices"][0]["message"]["content"] = "API响应缺少必要的content字段，无法提取结果。"
                
            # 处理DeepSeek的推理内容字段
            if settings.ENABLE_REASONING and "reasoning_content" in first_choice.get("message", {}):
                reasoning_content = first_choice["message"].get("reasoning_content", "")
                logger.debug(f"DeepSeek推理内容: {reasoning_content[:500]}...")
                
                # 可以根据需要对推理内容进行额外处理
                
            return response
            
        except Exception as e:
            logger.error(f"DeepSeek API请求失败: {str(e)}")
            # 返回一个模拟响应以避免崩溃
            return {
                "id": "error_id",
                "choices": [
                    {
                        "message": {
                            "content": f"API请求失败: {str(e)}"
                        },
                        "finish_reason": "error"
                    }
                ],
                "usage": {"total_tokens": 0},
                "model": self.model_name
            }

class CustomChatModel(BaseChatModel):
    """将现有LLM服务适配到LangChain框架的聊天模型类"""
    
    # 基本属性
    model_name: str = "openrouter"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    # 配置选项
    use_direct_connection: bool = False
    proxy: Optional[Dict[str, str]] = None
    _llm_service: Optional[OpenRouterLLMService] = None
    
    @property
    def _llm_type(self) -> str:
        """返回LLM类型标识"""
        return "custom_openrouter_chat"
    
    @property
    def llm_service(self) -> OpenRouterLLMService:
        """获取或创建LLM服务实例"""
        if self._llm_service is None:
            self._llm_service = get_llm_service(
                use_direct_connection=self.use_direct_connection,
                proxy=self.proxy,
                use_sdk=True
            )
        return self._llm_service
    
    def _convert_messages_to_openrouter_format(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """将LangChain消息格式转换为OpenRouter格式"""
        openrouter_messages = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                openrouter_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                openrouter_messages.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                openrouter_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, ChatMessage):
                role = message.role
                # OpenRouter API仅支持system、user、assistant角色
                if role not in ["system", "user", "assistant"]:
                    # 默认将未知角色转为user
                    role = "user"
                openrouter_messages.append({"role": role, "content": message.content})
            else:
                # 处理其他消息类型，默认作为user消息
                openrouter_messages.append({"role": "user", "content": str(message.content)})
        
        return openrouter_messages
    
    def _create_chat_result(self, response: Dict[str, Any]) -> ChatResult:
        """将OpenRouter响应转换为LangChain ChatResult"""
        generations = []
        
        if "error" in response and response["error"]:
            # 处理错误情况
            error_message = response.get("message", "Unknown error")
            logger.error(f"OpenRouter API error: {error_message}")
            
            # 创建一个错误消息的生成结果
            content = response.get("choices", [{}])[0].get("message", {}).get("content", 
                "抱歉，我遇到了技术问题，无法处理您的请求。请稍后再试。")
            generation = ChatGeneration(
                message=AIMessage(content=content),
                generation_info={"finish_reason": "error"}
            )
            generations.append(generation)
        else:
            # 处理正常情况
            for choice in response.get("choices", []):
                message_content = choice.get("message", {}).get("content", "")
                generation = ChatGeneration(
                    message=AIMessage(content=message_content),
                    generation_info={"finish_reason": choice.get("finish_reason")}
                )
                generations.append(generation)
        
        # 获取token使用信息
        token_usage = response.get("usage", {})
        llm_output = {"token_usage": token_usage, "model_name": response.get("model", self.model_name)}
        
        return ChatResult(generations=generations, llm_output=llm_output)
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成聊天完成结果"""
        # 不使用asyncio.run，避免在已有事件循环中嵌套
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 执行异步方法
        if loop.is_running():
            # 当前在事件循环中，不能直接使用run_until_complete
            logger.warning("在运行中的事件循环中调用同步方法，将使用替代方案")
            # 创建一个Future并在当前事件循环中安排它的执行
            future = asyncio.ensure_future(
                self._agenerate(messages, stop, run_manager, **kwargs)
            )
            # 阻塞直到Future完成
            while not future.done():
                # 给事件循环一些时间处理其他任务
                loop.run_until_complete(asyncio.sleep(0.01))
            return future.result()
        else:
            # 不在事件循环中，可以直接运行
            return loop.run_until_complete(
                self._agenerate(messages, stop, run_manager, **kwargs)
            )
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成聊天完成结果"""
        # 将消息转换为OpenRouter格式
        openrouter_messages = self._convert_messages_to_openrouter_format(messages)
        
        # 准备参数
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        # 调用LLM服务
        response = await self.llm_service.generate(
            messages=openrouter_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 转换结果
        return self._create_chat_result(response)


class WrappedChatOpenAI(ChatOpenAI):
    """封装ChatOpenAI以增强日志记录和错误处理"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> Any:
        """重写异步生成方法以添加日志记录"""
        start_time = time.perf_counter()
        
        try:
            # 记录请求信息
            prompt_str = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])
            logger.debug(f"发送请求到模型: {self.model_name}")
            
            # 调用原始方法
            response = await super()._agenerate(messages, stop, run_manager, **kwargs)
            
            # 记录详细日志
            elapsed_time = time.perf_counter() - start_time
            
            # 修复：增加更强健的错误处理
            if hasattr(response, "generations"):
                if response.generations is None:
                    logger.warning("响应的generations属性为None")
                elif len(response.generations) > 0:
                    first_gen = response.generations[0]
                    if first_gen:
                        message = first_gen[0].message if isinstance(first_gen, list) and len(first_gen) > 0 else None
                
                    # 记录token使用情况
                    token_usage = None
                    if hasattr(response, "llm_output") and response.llm_output:
                        token_usage = response.llm_output.get("token_usage")
                
                    # 详细日志记录
                    log_llm_request(
                        prompt=prompt_str,
                        response=message,
                        model=self.model_name,
                        tokens=token_usage,
                        time=elapsed_time
                    )
            else:
                logger.warning("响应缺少generations属性")
                log_llm_request(
                    prompt=prompt_str,
                    response="缺少结构化响应",
                    model=self.model_name,
                    tokens=None,
                    time=elapsed_time
                )
            
            return response
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            logger.error(f"LLM请求错误: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            
            # 返回带有错误信息的空响应，而不是直接抛出异常
            from langchain_core.outputs import ChatGeneration, ChatResult
            error_message = f"生成失败: {str(e)}"
            generation = ChatGeneration(
                message=AIMessage(content=error_message),
                generation_info={"finish_reason": "error"}
            )
            return ChatResult(generations=[[generation]], llm_output={"error": str(e)})


def get_langchain_chat_model(
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    use_direct_connection: bool = False,
    proxy: Optional[Dict[str, str]] = None
) -> BaseChatModel:
    """
    获取LangChain聊天模型
    
    Args:
        temperature: 温度参数
        max_tokens: 最大生成token数
        use_direct_connection: 是否使用直接连接
        proxy: 代理设置
    
    Returns:
        LangChain聊天模型
    """
    # 根据默认AI模型配置选择不同的模型
    if settings.DEFAULT_AI_MODEL.lower() == "deepseek":
        model_name = settings.DEEPSEEK_MODEL
        
        logger.info(f"使用LangChain与DeepSeek连接, 模型: {model_name}")
        
        try:
            # 构建模型参数
            model_kwargs = {
                "temperature": temperature
            }
            
            if max_tokens:
                model_kwargs["max_tokens"] = max_tokens
            
            # 创建ChatDeepSeek实例
            return ChatDeepSeek(
                model_name=model_name,
                **model_kwargs
            )
        except Exception as e:
            logger.error(f"初始化DeepSeek LangChain聊天模型失败: {str(e)}")
            raise
    elif settings.DEFAULT_AI_MODEL.lower() == "openrouter":
        model_name = settings.OPENROUTER_MODEL
        
        logger.info(f"使用LangChain与OpenRouter连接, 模型: {model_name}")
        
        try:
            # 创建ChatOpenRouter实例，优先使用这个专用类
            model_kwargs = {
                "temperature": temperature
            }
            
            if max_tokens:
                model_kwargs["max_tokens"] = max_tokens
            
            return ChatOpenRouter(
                model_name=model_name,
                **model_kwargs
            )
        except Exception as e:
            logger.error(f"初始化OpenRouter LangChain聊天模型失败，尝试使用通用CustomChatModel: {str(e)}")
            # 如果专用类失败，回退到CustomChatModel
            try:
                return CustomChatModel(
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_direct_connection=use_direct_connection,
                    proxy=proxy
                )
            except Exception as e2:
                logger.error(f"初始化CustomChatModel也失败: {str(e2)}")
            raise
    else:
        # 不支持的模型类型，默认使用DeepSeek
        logger.warning(f"不支持的AI模型类型: {settings.DEFAULT_AI_MODEL}，使用DeepSeek作为默认")
        model_name = settings.DEEPSEEK_MODEL
        
        try:
            # 构建模型参数
            model_kwargs = {
                "temperature": temperature
            }
            
            if max_tokens:
                model_kwargs["max_tokens"] = max_tokens
            
            # 创建ChatDeepSeek实例
            return ChatDeepSeek(
                model_name=model_name,
                **model_kwargs
            )
        except Exception as e:
            logger.error(f"初始化DeepSeek LangChain聊天模型失败: {str(e)}")
            raise


# 测试例子
async def test_langchain_chat_model():
    """测试LangChain聊天模型"""
    try:
        chat_model = get_langchain_chat_model(temperature=0.3)
        
        # 创建一个简单的提示
        messages = [
            SystemMessage(content="你是一个专业的数据分析师，你擅长分析电商数据并给出有价值的见解。"),
            HumanMessage(content="最近一个月有哪些产品销量最好？")
        ]
        
        logger.info("发送测试消息到LangChain聊天模型")
        start_time = time.perf_counter()
        
        response = await chat_model.ainvoke(messages)
        
        elapsed_time = time.perf_counter() - start_time
        logger.info(f"收到响应，耗时: {elapsed_time:.2f}秒")
        logger.info(f"响应内容: {response.content if hasattr(response, 'content') else str(response)}")
        
        return True
    except Exception as e:
        logger.error(f"测试LangChain聊天模型失败: {str(e)}")
        return False

def extract_content_from_response(response):
    """
    从LLM响应中提取内容，处理各种返回类型
    """
    # 添加None值处理
    if response is None:
        logger.warning("收到空响应(None)，无法提取内容")
        return "无法从空响应中提取内容"
        
    # 检查空字典或空列表
    if isinstance(response, dict) and not response:
        logger.warning("收到空字典响应，无法提取内容")
        return "收到空响应，请重试"
        
    if isinstance(response, list) and not response:
        logger.warning("收到空列表响应，无法提取内容")
        return "收到空响应列表，请重试"
    
    # 处理各种响应类型
    try:
        # 基本属性检查，使用安全的getattr和get方法
        if hasattr(response, "content"):
            return response.content
            
        if hasattr(response, "message"):
            message = getattr(response, "message", None)
            if message is not None and hasattr(message, "content"):
                return message.content
                
        # 字符串直接返回
        if isinstance(response, str):
            return response
            
        # 安全处理字典
        if isinstance(response, dict):
            # 直接content字段
            if "content" in response:
                return response["content"]
                
            # OpenAI/OpenRouter格式
            if "choices" in response:
                choices = response.get("choices")
                # 安全检查choices
                if choices is None:
                    logger.warning("响应中choices为None")
                    return "API返回了无效的响应格式"
                    
                if not isinstance(choices, list):
                    logger.warning(f"响应中choices不是列表: {type(choices)}")
                    return "API返回了意外的响应格式，choices应为列表"
                    
                if not choices:  # 空列表
                    logger.warning("响应中choices列表为空")
                    return "API未返回任何生成内容"
                
                # 获取第一个choice
                first_choice = choices[0]
                if not isinstance(first_choice, dict):
                    logger.warning(f"响应中first_choice不是字典: {type(first_choice)}")
                    return f"API返回了意外的choice格式: {first_choice}"
                
                # 检查message字段
                message = first_choice.get("message")
                if message is None:
                    logger.warning("响应中message为None")
                    
                    # 尝试直接从choice中获取文本，某些API可能直接提供text字段
                    if "text" in first_choice:
                        return first_choice["text"]
                        
                    return "API返回了无效的响应格式，缺少message字段"
                
                if not isinstance(message, dict):
                    logger.warning(f"响应中message不是字典: {type(message)}")
                    
                    # 如果message是字符串，可能直接就是内容
                    if isinstance(message, str):
                        return message
                        
                    return f"API返回了意外的message格式: {message}"
                
                # 从message中获取content
                if "content" in message:
                    content = message["content"]
                    if content is None:
                        logger.warning("响应中content为None")
                        return "API返回了空内容"
                    return content
                else:
                    logger.warning("响应中message缺少content字段")
                    # 尝试使用整个message作为内容
                    return str(message)
        
        # LangChain专用格式
        if hasattr(response, "generations"):
            generations = getattr(response, "generations", None)
            
            # 检查generations
            if generations is None:
                logger.warning("响应的generations属性为None")
                return "无法解析生成的回复，生成结果为空"
            
            # 检查是否可迭代且非空
            if not hasattr(generations, "__iter__"):
                logger.warning(f"响应的generations属性不可迭代: {type(generations)}")
                return "无法解析生成的回复，generations格式无效"
            
            try:
                # 安全地获取第一个generation
                generations_list = list(generations)
                if not generations_list:
                    logger.warning("响应的generations列表为空")
                    return "无法解析生成的回复，generations列表为空"
                
                generation = generations_list[0]
                
                # 尝试不同的提取路径
                if hasattr(generation, "message") and hasattr(generation.message, "content"):
                    return generation.message.content
                    
                if hasattr(generation, "text"):
                    return generation.text
                    
                # 检查是否为列表
                if isinstance(generation, list) and generation:
                    first_gen = generation[0]
                    if hasattr(first_gen, "message") and hasattr(first_gen.message, "content"):
                        return first_gen.message.content
                        
                # 如果是字典，尝试直接获取text或content字段
                if isinstance(generation, dict):
                    if "text" in generation:
                        return generation["text"]
                    if "content" in generation:
                        return generation["content"]
                    if "message" in generation and isinstance(generation["message"], dict):
                        msg = generation["message"]
                        if "content" in msg:
                            return msg["content"]
                
                # 尝试转为字符串
                return str(generation)
                
            except (TypeError, IndexError) as e:
                logger.error(f"处理generations时出错: {str(e)}")
                return f"处理LLM响应时出错: {str(e)}"
    
        # 最后尝试转为字符串
        return str(response)
        
    except Exception as e:
        logger.error(f"提取响应内容时出错: {str(e)}")
        return f"无法提取内容，处理响应时出错: {str(e)}"

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
    if isinstance(prompt, list):
        # 如果是消息列表，记录每条消息
        for i, msg in enumerate(prompt):
            msg_role = getattr(msg, "type", "unknown")
            msg_content = getattr(msg, "content", str(msg))
            logger.debug(f"提示词[{i}] - {msg_role}: {msg_content[:1000]}..." if len(msg_content) > 1000 else f"提示词[{i}] - {msg_role}: {msg_content}")
    elif isinstance(prompt, str):
        logger.debug(f"提示词: {prompt[:1000]}..." if len(prompt) > 1000 else f"提示词: {prompt}")
    else:
        logger.debug(f"提示词: {str(prompt)[:1000]}...")
    
    # 提取并记录响应内容
    content = extract_content_from_response(response)
    logger.debug(f"响应内容: {content[:1000]}..." if len(content) > 1000 else f"响应内容: {content}")
    
    if tokens:
        logger.debug(f"Token使用: {tokens}")
    if time:
        logger.debug(f"请求耗时: {time:.2f}秒")
    logger.debug("--------------------------")
    
    return content  # 返回提取的内容

class LangChainAdapter:
    """LangChain适配器类，将LLM包装为LangChain兼容的接口"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """初始化LangChain适配器
        
        Args:
            model_name: 使用的模型名称
            temperature: 温度参数
            max_tokens: 最大生成token数
        """
        self.model_name = model_name
        self.temperature = temperature 
        self.max_tokens = max_tokens
        self.llm = None
        
        # 初始化LLM
        self._init_llm()
        
    def _init_llm(self):
        """初始化LLM，根据配置选择合适的LLM实现"""
        if self.llm:
            return
            
        try:
            # 根据默认AI模型配置选择不同的模型
            if settings.DEFAULT_AI_MODEL.lower() == "deepseek":
                model_name = self.model_name or settings.DEEPSEEK_MODEL
                
                # 使用DeepSeek API
                logger.info(f"初始化DeepSeek LLM: {model_name}")
                self.llm = ChatDeepSeek(
                    model_name=model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
            elif settings.DEFAULT_AI_MODEL.lower() == "openrouter":
                model_name = self.model_name or settings.OPENROUTER_MODEL
                
                # 使用OpenRouter专用类
                logger.info(f"初始化OpenRouter LLM: {model_name}")
                try:
                    self.llm = ChatOpenRouter(
                        model_name=model_name,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                except Exception as e:
                    logger.error(f"初始化ChatOpenRouter失败，回退到通用实现: {str(e)}")
                    # 回退到CustomChatModel
                    self.llm = CustomChatModel(
                        model_name=model_name,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
            else:
                # 默认使用DeepSeek
                model_name = self.model_name or settings.DEEPSEEK_MODEL
                logger.warning(f"未知的LLM类型: {settings.DEFAULT_AI_MODEL}，使用DeepSeek作为默认")
                
                self.llm = ChatDeepSeek(
                    model_name=model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
            logger.info(f"初始化LLM成功: {model_name}")
        except Exception as e:
            logger.error(f"初始化LLM失败: {str(e)}")
            self.llm = None
            raise
            
    async def generate(
        self,
        prompt: Union[str, List[BaseMessage]],
        system_message: Optional[str] = None,
        max_tokens: Optional[int] = 1024
    ) -> str:
        """生成文本响应"""
        start_time = time.perf_counter()
        
        try:
            # 初始化LLM（如果需要）
            if not self.llm:
                self._init_llm()
                if not self.llm:
                    # 初始化失败的情况
                    logger.error("LLM初始化失败，无法生成回复")
                    return "抱歉，LLM服务初始化失败，无法生成回复"
            
            # 处理消息格式
            if isinstance(prompt, str):
                messages = []
                
                # 添加系统消息（如果提供）
                if system_message:
                    messages.append(SystemMessage(content=system_message))
                
                # 添加用户消息
                messages.append(HumanMessage(content=prompt))
            else:
                # 假设已经是消息列表
                messages = prompt
            
            # 记录查询信息
            logger.info(f"使用模型 {self.model_name} 生成响应")
            
            # 调用LLM
            try:
                # 设置超时
                response = await asyncio.wait_for(
                    self.llm.ainvoke(
                        messages,
                        max_tokens=max_tokens
                    ),
                    timeout=60  # 60秒超时
                )
                
                # 处理可能为None的响应
                if response is None:
                    logger.warning("LLM返回了空响应(None)")
                    elapsed_time = time.perf_counter() - start_time
                    logger.error(f"LLM调用失败: 返回了None, 耗时: {elapsed_time:.2f}秒")
                    return "生成回复失败，LLM返回了空响应"
                
                # 记录原始响应以便调试
                logger.debug(f"LLM原始响应: {type(response)} - {response}")
            
                # 提取回复内容
                if isinstance(response, dict):
                    if "choices" in response and response["choices"]:
                        content = response["choices"][0].get("message", {}).get("content", "")
                        if content:
                            return content
                    if "content" in response:
                        return response["content"]
                
                # 提取AIMessage中的内容
                if hasattr(response, "content"):
                    return response.content
                    
                # 处理字符串回复
                if isinstance(response, str):
                    return response
                
                # 返回响应的字符串表示（如果以上提取方法都失败）
                return str(response)
                
            except asyncio.TimeoutError:
                elapsed_time = time.perf_counter() - start_time
                logger.error(f"LLM调用超时，耗时: {elapsed_time:.2f}秒")
                return "抱歉，生成回复超时，请稍后重试或调整查询"
                
            except Exception as e:
                elapsed_time = time.perf_counter() - start_time
                logger.error(f"LLM调用失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
                return f"生成回复失败: {str(e)}"
                
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            logger.error(f"生成文本响应失败: {str(e)}, 耗时: {elapsed_time:.2f}秒")
            return f"处理请求时出错: {str(e)}"

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        流式生成LLM响应
        
        Args:
            prompt: 提示文本
            
        Yields:
            生成的文本块
        """
        logger.info(f"使用模型 {self.model_name} 流式生成响应")
        
        try:
            # 确保我们的LLM支持流式输出
            if hasattr(self.llm, "stream") and callable(getattr(self.llm, "stream")):
                # 检查stream方法返回的是否为异步生成器
                stream_result = self.llm.stream(prompt)
                
                # 判断返回值类型
                if hasattr(stream_result, "__aiter__"):
                    # 如果支持异步迭代，使用async for
                    async for chunk in stream_result:
                        if isinstance(chunk, dict) and "content" in chunk:
                            yield chunk["content"]
                        elif hasattr(chunk, "content"):
                            yield chunk.content
                        else:
                            yield str(chunk)
                else:
                    # 如果是普通生成器，使用普通for循环
                    logger.info("LLM.stream返回的是普通生成器，使用同步方式处理")
                    for chunk in stream_result:
                        if isinstance(chunk, dict) and "content" in chunk:
                            yield chunk["content"]
                        elif hasattr(chunk, "content"):
                            yield chunk.content
                        else:
                            yield str(chunk)
                        # 在同步迭代中使用yield之后，需要异步暂停一下，让事件循环有机会处理其他任务
                        await asyncio.sleep(0)
                        
            elif self.model_name.startswith("deepseek"):
                # 使用DeepSeek API的流式功能
                from openai import AsyncOpenAI
                
                client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base if self.api_base else "https://api.deepseek.com"
                )
                
                response = await client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    temperature=0.7,
                    max_tokens=1500
                )
                
                async for chunk in response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        if hasattr(chunk.choices[0], "delta") and hasattr(chunk.choices[0].delta, "content"):
                            delta_content = chunk.choices[0].delta.content
                            if delta_content:
                                yield delta_content
            else:
                # 回退到非流式方式，然后模拟流式输出
                response = await self.generate(prompt)
                # 按字符模拟流式输出
                for i in range(0, len(response), 2):
                    yield response[i:i+2]
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"流式生成出错: {str(e)}")
            # 在错误情况下，我们也要让生成器正常结束
            yield f"[生成错误: {str(e)}]"
            raise