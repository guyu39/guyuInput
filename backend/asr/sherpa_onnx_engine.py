"""
sherpa-onnx 离线语音识别引擎
基于 sherpa-onnx SenseVoice CTC 模型，完全本地运行，无需网络，支持异步预加载
"""
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sherpa_onnx

from .base import ASREngine, ASRResult

logger = logging.getLogger('guyuInput')

# 默认模型路径（相对于项目根目录）
_MODEL_DIR = Path(__file__).parent.parent.parent / "models"


class SherpaOnnxEngine(ASREngine):
    """sherpa-onnx 离线识别引擎 — 非流式 SenseVoice CTC 模型，支持异步预加载"""

    def __init__(
        self,
        model_dir: str = str(_MODEL_DIR),
        num_threads: int = 2,
    ):
        super().__init__()
        self.model_dir = Path(model_dir)
        self.num_threads = num_threads
        self.model_path = self.model_dir / "model.int8.onnx"
        self.tokens_path = self.model_dir / "tokens.txt"
        self._recognizer: Optional[sherpa_onnx.OfflineRecognizer] = None
        self._buffer: list = []
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

        logger.info("后台预加载 sherpa-onnx SenseVoice 模型...")
        t = threading.Thread(target=self._load_worker, daemon=True, name="sherpa-preload")
        t.start()

    def _load_worker(self):
        """后台加载工作线程"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"SenseVoice 模型不存在: {self.model_path}\n"
                    f"请将 model.int8.onnx 和 tokens.txt 放到 {self.model_dir}"
                )
            if not self.tokens_path.exists():
                raise FileNotFoundError(
                    f"tokens 文件不存在: {self.tokens_path}"
                )

            self._recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(self.model_path),
                tokens=str(self.tokens_path),
                num_threads=self.num_threads,
                language="auto",
                use_itn=True,
                decoding_method="greedy_search",
            )
            self._loaded = True
            logger.info("sherpa-onnx 模型预加载完成")
        except FileNotFoundError as e:
            self._load_error = str(e)
            logger.warning(str(e))
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"sherpa-onnx 模型加载失败: {e}")
        finally:
            with self._load_lock:
                self._loading = False
            self._load_done.set()

    def _ensure_model(self):
        """同步加载模型 — 作为预加载失败或未启动时的后备方案"""
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
            logger.info("等待 sherpa-onnx 模型加载完成...")
            self._load_done.wait()

        if self._load_error:
            raise FileNotFoundError(self._load_error)

    def start(
        self,
        on_result: Callable[[ASRResult], None],
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """启动识别会话 — 清空缓冲区，准备接收音频"""
        try:
            self._ensure_model()
        except FileNotFoundError as e:
            if on_error:
                on_error(str(e))
            return

        self._on_result = on_result
        self._on_error = on_error
        self._buffer.clear()
        self._is_running = True
        logger.debug("离线识别会话已启动")

    def feed_audio(self, audio_data: np.ndarray):
        """缓冲音频帧，在 stop 时一次性识别"""
        if self._is_running:
            self._buffer.append(audio_data.copy())

    def stop(self):
        """停止录音，执行识别并回调结果"""
        if not self._is_running:
            return

        self._is_running = False

        if not self._buffer or self._recognizer is None:
            return

        # 合并所有缓冲的音频帧
        audio = np.concatenate(self._buffer)
        self._buffer.clear()

        try:
            # 确保是 1D float32 数组
            if audio.ndim > 1:
                audio = audio[:, 0]
            audio = audio.astype(np.float32)

            # 非流式识别
            stream = self._recognizer.create_stream()
            stream.accept_waveform(16000, audio)
            self._recognizer.decode_stream(stream)

            text = stream.result.text.strip()
            logger.info(f"离线识别结果 ({len(audio)/16000:.1f}s): {text[:50]}")

            if text and self._on_result:
                self._on_result(ASRResult(text=text, is_final=True, is_partial=False))
        except Exception as e:
            logger.error(f"sherpa-onnx 识别失败: {e}")
            if self._on_error:
                self._on_error(f"离线识别失败: {e}")
