"""
FunASR 离线语音识别引擎
基于达摩院 Paraformer 流式模型，支持异步预加载
"""
import logging
import threading
from typing import Callable, Optional

import numpy as np

from .base import ASREngine, ASRResult

logger = logging.getLogger('guyuInput')

# 默认模型（从 ModelScope 下载）
DEFAULT_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"


class FunASREngine(ASREngine):
    """FunASR Paraformer 离线流式识别引擎 — 支持异步预加载"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        super().__init__()
        self.model_name = model_name
        self._model = None
        self._cache: dict = {}
        self._is_running = False

        # 异步加载状态
        self._loaded = False
        self._loading = False
        self._load_error: Optional[str] = None
        self._load_lock = threading.Lock()
        self._load_done = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_ready(self) -> bool:
        """模型是否已加载完成"""
        return self._loaded

    @property
    def is_loading(self) -> bool:
        """模型是否正在后台加载中"""
        return self._loading

    @property
    def load_error(self) -> Optional[str]:
        """加载失败的错误信息"""
        return self._load_error

    def preload_async(self):
        """后台线程异步预加载模型，避免首次使用时卡 UI"""
        with self._load_lock:
            if self._loaded or self._loading:
                return
            self._loading = True
            self._load_done.clear()

        logger.info(f"后台预加载 FunASR 模型: {self.model_name}")
        t = threading.Thread(target=self._load_worker, daemon=True, name="funasr-preload")
        t.start()

    def _load_worker(self):
        """后台加载工作线程"""
        try:
            from funasr import AutoModel
            self._model = AutoModel(
                model=self.model_name,
                device="cpu",
                disable_pbar=True,
                disable_log=True,
            )
            self._loaded = True
            logger.info("FunASR 模型预加载完成")
        except ImportError:
            self._load_error = "离线引擎未安装，请切换到在线模式"
            logger.warning("FunASR 未安装")
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"FunASR 模型加载失败: {e}")
        finally:
            with self._load_lock:
                self._loading = False
            self._load_done.set()

    def load_model(self):
        """同步加载模型 — 作为预加载失败或未启动时的后备方案

        注意：若后台预加载进行中，此方法会阻塞等待。调用者应先通过
        is_ready / is_loading 判断状态，避免在 GUI 线程阻塞。
        """
        with self._load_lock:
            if self._loaded:
                return
            if not self._loading:
                self._loading = True
                self._load_done.clear()
                self._load_worker()
                return

        # 已在后台加载中，等待完成
        if self._loading and not self._loaded:
            logger.info("等待 FunASR 模型加载完成...")
            self._load_done.wait()

        if self._load_error:
            raise RuntimeError(self._load_error)

    def wait_ready(self, timeout: float = 30.0) -> bool:
        """轮询等待模型加载完成，适配 GUI 线程的 processEvents 注入

        由调用者在循环中调用 QApplication.processEvents() 保持 UI 响应。
        返回 True 表示加载完成，False 表示超时。
        """
        if self._loaded:
            return True
        return self._load_done.wait(timeout=timeout) and self._loaded

    def start(self, on_result: Callable[[ASRResult], None],
              on_error: Optional[Callable[[str], None]] = None):
        try:
            self.load_model()
        except RuntimeError as e:
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
