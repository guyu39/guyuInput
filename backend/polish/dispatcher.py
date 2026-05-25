"""润色调度器"""
import logging
from typing import Optional

from .base import BasePolisher, PolishMode

logger = logging.getLogger('guyuInput')


class PolishDispatcher:
    """润色调度器 — 封装超时降级逻辑"""

    def __init__(self, polisher: Optional[BasePolisher] = None):
        self._polisher = polisher

    @property
    def is_available(self) -> bool:
        return self._polisher is not None

    def set_polisher(self, polisher: Optional[BasePolisher]):
        self._polisher = polisher

    def polish(self, text: str, mode: PolishMode) -> str:
        """执行润色。失败时返回原文。"""
        if not self._polisher:
            return text

        try:
            result = self._polisher.polish(text, mode)
            if result and result.strip():
                return result.strip()
            logger.warning("润色返回空文本，降级使用原文")
            return text
        except Exception as e:
            logger.warning(f"润色失败，降级使用原文: {e}")
            return text
