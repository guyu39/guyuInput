"""
FunASR 离线语音识别引擎
基于达摩院 Paraformer 流式模型
"""
import logging
from typing import Callable, Optional

import numpy as np

from .base import ASREngine, ASRResult

logger = logging.getLogger('guyuInput')

# 默认模型（从 ModelScope 下载）
DEFAULT_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"


class FunASREngine(ASREngine):
    """FunASR Paraformer 离线流式识别引擎"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        super().__init__()
        self.model_name = model_name
        self._model = None
        self._cache: dict = {}
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def load_model(self):
        """延迟加载模型 - 第一次使用离线模式时才加载，加速启动"""
        if self._model is not None:
            return

        logger.info(f"正在加载 FunASR 模型: {self.model_name}")
        try:
            from funasr import AutoModel
            self._model = AutoModel(
                model=self.model_name,
                device="cpu",
                disable_pbar=True,
                disable_log=True,
            )
            logger.info("FunASR 模型加载完成")
        except ImportError:
            raise ImportError("离线引擎未安装，请切换到在线模式")

    def start(self, on_result: Callable[[ASRResult], None], on_error: Optional[Callable[[str], None]] = None):
        try:
            self.load_model()
        except ImportError as e:
            if on_error:
                on_error(str(e))
            return

        self._on_result = on_result
        self._on_error = on_error
        self._cache = {}
        self._is_running = True

    def feed_audio(self, audio_data: np.ndarray):
        if not self._is_running or self._model is None:
            return

        try:
            res = self._model.generate(
                input=audio_data,
                cache=self._cache,
                is_final=False,
                chunk_size=[0, 10, 5],
            )
            if res and len(res) > 0:
                text = res[0].get('text', '')
                if text and self._on_result:
                    self._on_result(ASRResult(text=text, is_final=False, is_partial=True))
        except Exception as e:
            logger.warning(f"FunASR 识别错误: {e}")

    def stop(self):
        if not self._is_running or self._model is None:
            return

        try:
            # 发送最后一帧获取最终结果
            res = self._model.generate(
                input=np.zeros(1024, dtype=np.float32),
                cache=self._cache,
                is_final=True,
            )
            if res and len(res) > 0:
                text = res[0].get('text', '')
                if text and self._on_result:
                    self._on_result(ASRResult(text=text, is_final=True, is_partial=False))
        except Exception as e:
            logger.warning(f"FunASR 最终结果获取失败: {e}")

        self._is_running = False
        self._cache = {}
