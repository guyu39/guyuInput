"""
后端 API 类 - Qt 信号版本
所有前端事件通过 Qt 信号推送，替代 pywebview JS Bridge
"""
import logging
import json
import threading
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from .config import ConfigManager
from .audio import AudioCapture
from .hotkey import HotkeyManager
from .input import TextInjector
from .asr import (
    ASRDispatcher, XunfeiASR, AliASR, DoubaoASR, MiniMaxASR,
    SherpaOnnxEngine, ASRResult, ASRMode,
)

logger = logging.getLogger('guyuInput')


class API(QObject):
    """后端 API - Qt 信号驱动的通信层"""

    # ================================================================
    # Qt 信号定义
    # ================================================================
    recording_started = Signal(str)       # engine name
    recording_stopped = Signal(str, bool) # text, injected
    recording_error = Signal(str)         # error message
    volume_changed = Signal(float)        # volume level
    silence_timeout = Signal()
    asr_partial = Signal(str)             # partial recognition text
    asr_final = Signal(str)               # final recognition text
    asr_error = Signal(str)               # ASR error
    config_loaded = Signal(str)           # all config as JSON
    devices_loaded = Signal(str)          # audio devices JSON
    window_resize = Signal(int, int)      # width, height
    window_show = Signal()
    window_hide = Signal()

    PROVIDER_KEYS = {
        "xunfei": ["app_id", "api_key", "api_secret"],
        "doubao": ["app_id", "access_token"],
        "ali": ["access_key_id", "access_key_secret", "app_key"],
        "minimax": ["api_key", "group_id"],
    }

    PROVIDER_CLASSES = {
        "xunfei": XunfeiASR,
        "doubao": DoubaoASR,
        "ali": AliASR,
        "minimax": MiniMaxASR,
    }

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config

        # 核心模块
        self.audio = AudioCapture()
        self.hotkey = HotkeyManager(config.get('record_hotkey', 'ctrl+alt+v'))
        self.injector = TextInjector()

        # 在线 ASR 引擎（四个供应商）
        self._online_engines = {}
        self._init_engines()
        self.offline_engine = SherpaOnnxEngine()
        self.asr_mode = ASRMode(config.get('asr_mode', 'auto'))

        provider = config.get('asr_provider', 'xunfei')
        self.dispatcher = ASRDispatcher(
            mode=self.asr_mode,
            online_engines=self._online_engines,
            offline_engine=self.offline_engine,
        )
        self.dispatcher.set_provider(provider)

        # 录音状态
        self._recognized_text: str = ""
        self._accumulated_text: str = ""
        self._silence_timer: Optional[threading.Timer] = None

        # 绑定快捷键
        self.hotkey.register_callbacks(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

    def _init_engines(self):
        """根据配置初始化所有在线引擎"""
        for provider, cls in self.PROVIDER_CLASSES.items():
            creds = {}
            for key in self.PROVIDER_KEYS[provider]:
                creds[key] = self.config.get(f"{provider}_{key}", "")
            self._online_engines[provider] = cls(**creds)

    def _sync_engine_creds(self, provider: str):
        """同步单个引擎的凭证"""
        engine = self._online_engines.get(provider)
        if not engine:
            return
        for key in self.PROVIDER_KEYS[provider]:
            val = self.config.get(f"{provider}_{key}", "")
            setattr(engine, key, val)

    # ================================================================
    # 基础方法（由 main.py 直接调用）
    # ================================================================

    def get_config(self, key: str, default: str = "") -> str:
        return self.config.get(key, default)

    def set_config(self, key: str, value: str) -> bool:
        try:
            self.config.set(key, value)
            if key == 'record_hotkey':
                self.hotkey.set_hotkey(value)
            elif key == 'asr_mode':
                try:
                    self.dispatcher.mode = ASRMode(value)
                except ValueError:
                    pass
            elif key == 'asr_provider':
                self.dispatcher.set_provider(value)
            # 凭证相关：更新对应引擎
            for provider in self.PROVIDER_KEYS:
                if key.startswith(f"{provider}_"):
                    self._sync_engine_creds(provider)
                    break
            return True
        except Exception as e:
            logger.error(f"Set config failed: {e}")
            return False

    def load_all_config(self):
        """加载配置并推送到前端"""
        cur = self.config.conn.execute("SELECT key, value FROM config")
        rows = cur.fetchall()
        data = json.dumps({row[0]: row[1] for row in rows}, ensure_ascii=False)
        self.config_loaded.emit(data)

    def load_devices(self):
        """加载音频设备列表"""
        try:
            devices = AudioCapture.list_devices()
            result = [
                {"id": d.id, "name": d.name, "is_default": d.is_default}
                for d in devices
            ]
            self.devices_loaded.emit(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            logger.error(f"获取音频设备失败: {e}")
            self.devices_loaded.emit(json.dumps([]))

    def set_asr_mode(self, mode: str) -> bool:
        try:
            self.dispatcher.mode = ASRMode(mode)
            self.config.set('asr_mode', mode)
            return True
        except (ValueError, Exception) as e:
            logger.error(f"设置 ASR 模式失败: {e}")
            return False

    def save_asr_credentials(self, provider: str, credentials_json: str) -> bool:
        try:
            creds = json.loads(credentials_json)
            for k, v in creds.items():
                self.config.set(f"{provider}_{k}", v)
            # 保存供应商标识
            self.config.set('asr_provider', provider)
            # 同步引擎凭证
            self._sync_engine_creds(provider)
            # 切换调度器的活跃引擎
            self.dispatcher.set_provider(provider)
            logger.info(f"已保存 {provider} 凭证并切换引擎")
            return True
        except Exception as e:
            logger.error(f"保存凭证失败: {e}")
            return False

    def shutdown(self):
        self.hotkey.unregister()

    # ================================================================
    # 录音控制
    # ================================================================

    def start_recording(self, device_id: int = -1):
        try:
            self._recognized_text = ""
            self._accumulated_text = ""

            # 前置检查：在线 / 自动模式下，当前供应商是否有凭证
            if self.dispatcher.mode != ASRMode.OFFLINE:
                engine = self.dispatcher._get_online_engine()
                if engine is None:
                    self.recording_error.emit("在线引擎未初始化，请配置 API 凭证")
                    return
                # 检查凭证是否为空
                provider = self.dispatcher.provider
                keys = self.PROVIDER_KEYS.get(provider, [])
                has_creds = any(self.config.get(f"{provider}_{k}", "") for k in keys)
                if not has_creds:
                    provider_names = {"xunfei": "讯飞", "doubao": "豆包", "ali": "阿里", "minimax": "MiniMax"}
                    self.recording_error.emit(f"请先配置 {provider_names.get(provider, provider)} API 凭证")
                    return

            self.dispatcher.start(
                on_result=self._on_asr_result,
                on_error=self._on_asr_error,
            )

            dev = device_id if device_id >= 0 else None
            self.audio.start(
                audio_callback=self._on_audio_data,
                volume_callback=self._on_volume,
                device_id=dev,
            )

            self._reset_silence_timer()
            self.recording_started.emit(self.dispatcher.current_engine_name)

            # 离线模式无流式输出，显示占位文字避免主显示区域空白
            if self.dispatcher.current_engine_name == "offline":
                self.asr_partial.emit("正在聆听...")
        except Exception as e:
            logger.error(f"启动录音失败: {e}")
            self.recording_error.emit(str(e))

    def stop_recording(self, confirm: bool = True):
        self.audio.stop()

        # 离线模式：先刷新 UI 显示"识别中..."，再同步阻塞识别
        if confirm and self.dispatcher.current_engine_name == "offline":
            self.asr_partial.emit("识别中...")
            QApplication.processEvents()

        self.dispatcher.stop()
        self._cancel_silence_timer()

        if confirm and self._recognized_text.strip():
            text = self._recognized_text.strip()
            self.hotkey.suppress_temporarily(0.5)
            self.injector.inject_text(text)
            self.recording_stopped.emit(text, True)
        else:
            self.recording_stopped.emit("", False)

    # ================================================================
    # 音频回调
    # ================================================================

    def _on_audio_data(self, audio_data: np.ndarray):
        self.dispatcher.feed_audio(audio_data)

    def _on_volume(self, volume: float):
        self._reset_silence_timer()
        self.volume_changed.emit(volume)

    def _reset_silence_timer(self):
        if self._silence_timer:
            self._silence_timer.cancel()
        self._silence_timer = threading.Timer(3.0, self._on_silence_timeout)
        self._silence_timer.daemon = True
        self._silence_timer.start()

    def _cancel_silence_timer(self):
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None

    def _on_silence_timeout(self):
        self.silence_timeout.emit()

    # ================================================================
    # ASR 回调
    # ================================================================

    def _on_asr_result(self, result: ASRResult):
        if result.is_partial:
            display = self._accumulated_text + result.text
            self._recognized_text = display
            self.asr_partial.emit(display)
        else:
            self._accumulated_text += result.text
            self._recognized_text = self._accumulated_text
            self.asr_final.emit(self._accumulated_text)

    def _on_asr_error(self, err: str):
        logger.warning(f"ASR 错误: {err}")
        self.asr_error.emit(err)

    # ================================================================
    # 快捷键回调
    # ================================================================

    def _on_hotkey_press(self):
        logger.info("快捷键按下，开始录音")
        self.start_recording()

    def _on_hotkey_release(self):
        logger.info("快捷键松开，停止录音")
        self.stop_recording(confirm=True)
