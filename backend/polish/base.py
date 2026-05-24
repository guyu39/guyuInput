"""AI 润色抽象基类"""
from abc import ABC, abstractmethod
from enum import Enum


class PolishMode(Enum):
    LIGHT = "light"        # 仅标点
    MODERATE = "moderate"  # 适度润色（默认）
    DEEP = "deep"          # 深度润色


class BasePolisher(ABC):
    """LLM 润色器抽象基类"""

    @abstractmethod
    def polish(self, text: str, mode: PolishMode) -> str:
        """执行润色，返回润色后文本"""
