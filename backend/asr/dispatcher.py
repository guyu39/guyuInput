"""
ASR 调度器 - 负责多供应商切换和在线/离线引擎调度
"""
import logging
from typing import Callable, Optional, Dict

import numpy as np

from .base import ASREngine, ASRResult, ASRMode

logger = logging.getLogger('guyuInput')

PROVIDER_ENGINE_KEYS = {
    "xunfei": "xunfei",
    "ali": "ali",
    "doubao": "doubao",
    "minimax": "minimax",
}


class ASRDispatcher:
    """
    ASR 调度器
    - 支持多供应商在线引擎 (讯飞/阿里/豆包/MiniMax)
    - 离线兜底: 网络异常时自动降级到 FunASR
    - 支持手动切换仅在线 / 仅离线 / 自动
    """

    def __init__(
        self,
        mode: ASRMode = ASRMode.AUTO,
        online_engines: Optional[Dict[str, ASREngine]] = None,
        offline_engine: Optional[ASREngine] = None,
    ):
        self.mode = mode
        self._online_engines = online_engines or {}
        self.offline = offline_engine
        self._provider = "xunfei"  # 默认供应商
        self._current_engine: Optional[ASREngine] = None
        self._current_engine_name: str = ""
        self._on_result: Optional[Callable[[ASRResult], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._is_recording = False
        self._online_failed = False
        self._pending_audio: list = []

    @property
    def current_engine_name(self) -> str:
        return self._current_engine_name

    @property
    def provider(self) -> str:
        return self._provider

    @provider.setter
    def provider(self, value: str):
        if value in self._online_engines:
            self._provider = value

    def set_provider(self, provider: str):
        self.provider = provider

    def set_mode(self, mode: ASRMode):
        self.mode = mode

    def _get_online_engine(self) -> Optional[ASREngine]:
        return self._online_engines.get(self._provider)

    def start(self, on_result: Callable[[ASRResult], None], on_error: Optional[Callable[[str], None]] = None):
        self._on_result = on_result
        self._on_error = on_error
        self._is_recording = True
        self._pending_audio.clear()

        if self.mode == ASRMode.OFFLINE:
            self._start_offline()
        elif self.mode == ASRMode.ONLINE:
            if not self._try_start_online():
                if on_error:
                    on_error("在线模式不可用，请配置 API 凭证或切换到离线模式")
        else:  # AUTO
            if self._online_failed:
                self._start_offline()
            elif not self._try_start_online():
                self._start_offline()

    def feed_audio(self, audio_data: np.ndarray):
        if not self._is_recording:
            return

        if self._current_engine:
            self._current_engine.feed_audio(audio_data)
        else:
            self._pending_audio.append(audio_data.copy())

    def stop(self):
        self._is_recording = False

        if self._current_engine:
            self._current_engine.stop()

        self._current_engine = None
        self._current_engine_name = ""

    def _try_start_online(self) -> bool:
        engine = self._get_online_engine()
        if not engine:
            return False

        try:
            engine.start(
                on_result=self._on_online_result,
                on_error=self._on_online_error,
            )
            self._current_engine = engine
            self._current_engine_name = "online"
            self._online_failed = False
            logger.info(f"ASR 调度: 使用在线引擎 ({self._provider})")
            self._flush_pending_audio()
            return True
        except Exception as e:
            logger.warning(f"在线引擎启动失败 ({self._provider}): {e}")
            return False

    def _start_offline(self):
        if not self.offline:
            if self._on_error:
                self._on_error("离线引擎不可用，请安装 FunASR")
            return

        try:
            self.offline.start(
                on_result=self._on_result if self._on_result else lambda r: None,
                on_error=self._on_error,
            )
            self._current_engine = self.offline
            self._current_engine_name = "offline"
            logger.info("ASR 调度: 使用离线引擎")
            self._flush_pending_audio()
        except Exception as e:
            logger.error(f"离线引擎启动失败: {e}")
            if self._on_error:
                self._on_error(f"离线识别启动失败: {e}")

    def _on_online_result(self, result: ASRResult):
        if self._on_result:
            self._on_result(result)

    def _on_online_error(self, err: str):
        logger.warning(f"在线 ASR 错误: {err}")

        if self.mode == ASRMode.AUTO and not self._online_failed:
            self._online_failed = True
            if self._current_engine:
                try:
                    self._current_engine.stop()
                except Exception:
                    pass
            if self._is_recording:
                self._start_offline()
                return  # 自动降级成功，不向上传播错误

        # ONLINE 模式或 AUTO 降级失败 → 向上传播错误
        if self._on_error:
            self._on_error(err)

    def _flush_pending_audio(self):
        if not self._pending_audio or not self._current_engine:
            return
        for data in self._pending_audio:
            self._current_engine.feed_audio(data)
        self._pending_audio.clear()
