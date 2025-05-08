from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

class ConversationMemory:
    """
    对话记忆类，负责保存和管理历史查询和上下文
    """
    
    def __init__(self, window_size: int = 5):
        """
        初始化对话记忆
        
        Args:
            window_size: 记忆窗口大小，保存的历史交互数量
        """
        self.window_size = window_size
        self.interactions = []
        
    def add_interaction(self, user_message: str, assistant_message: Union[str, Dict[str, Any]]):
        """
        添加一轮对话交互
        
        Args:
            user_message: 用户消息
            assistant_message: 助手消息，可以是字符串或字典
        """
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "assistant": assistant_message
        }
        
        self.interactions.append(interaction)
        
        # 保持记忆在窗口大小内
        if len(self.interactions) > self.window_size:
            self.interactions = self.interactions[-self.window_size:]
    
    def get_interactions(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取最近的交互记录
        
        Args:
            count: 获取的记录数量，如果为None则返回全部
            
        Returns:
            交互记录列表
        """
        if count is None or count >= len(self.interactions):
            return self.interactions.copy()
        else:
            return self.interactions[-count:]
    
    def get_last_user_message(self) -> Optional[str]:
        """
        获取最后一条用户消息
        
        Returns:
            最后一条用户消息，如果没有则返回None
        """
        if not self.interactions:
            return None
        
        return self.interactions[-1]["user"]
    
    def get_last_assistant_message(self) -> Optional[Union[str, Dict[str, Any]]]:
        """
        获取最后一条助手消息
        
        Returns:
            最后一条助手消息，如果没有则返回None
        """
        if not self.interactions:
            return None
        
        return self.interactions[-1]["assistant"]
    
    def clear(self):
        """
        清空记忆
        """
        self.interactions = []
    
    def format_as_context(self) -> str:
        """
        将记忆格式化为上下文字符串，用于向LLM提供历史上下文
        
        Returns:
            格式化的上下文字符串
        """
        if not self.interactions:
            return "没有历史对话。"
        
        context = "历史对话：\n\n"
        
        for i, interaction in enumerate(self.interactions):
            context += f"用户: {interaction['user']}\n"
            
            # 处理不同类型的助手回复
            assistant_message = interaction["assistant"]
            if isinstance(assistant_message, dict):
                # 如果是字典，优先使用explanation，其次是整个字典
                if "explanation" in assistant_message:
                    context += f"助手: {assistant_message['explanation']}\n"
                else:
                    context += f"助手: {json.dumps(assistant_message, ensure_ascii=False)}\n"
            else:
                context += f"助手: {assistant_message}\n"
            
            context += "\n"
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将记忆转换为字典，用于序列化
        
        Returns:
            记忆字典
        """
        return {
            "window_size": self.window_size,
            "interactions": self.interactions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """
        从字典创建记忆实例
        
        Args:
            data: 记忆字典
            
        Returns:
            记忆实例
        """
        memory = cls(window_size=data.get("window_size", 5))
        memory.interactions = data.get("interactions", [])
        return memory 