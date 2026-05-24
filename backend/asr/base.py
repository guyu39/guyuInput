"""
ASR 引擎抽象基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

import numpy as np


class ASRMode(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AUTO = "auto"


@dataclass
class ASRResult:
    text: str
    is_final: bool = False
    is_partial: bool = True


class ASREngine(ABC):
    """ASR 引擎抽象基类，所有在线/离线引擎必须实现此接口"""

    def __init__(self):
        self._on_result: Optional[Callable[[ASRResult], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    @abstractmethod
    def start(self, on_result: Callable[[ASRResult], None], on_error: Optional[Callable[[str], None]] = None):
        """启动识别会话"""

    @abstractmethod
    def feed_audio(self, audio_data: np.ndarray):
        """送入音频数据 (float32, 16000Hz, 单声道)"""

    @abstractmethod
    def stop(self):
        """停止识别，返回最终结果"""

    @property
    def is_running(self) -> bool:
        """当前是否正在识别"""
        return False
