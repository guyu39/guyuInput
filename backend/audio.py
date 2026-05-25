"""
音频采集模块 - 基于 sounddevice 的麦克风录音
"""
import logging
from typing import Callable, Optional, List
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

logger = logging.getLogger('guyuInput')


@dataclass
class AudioDevice:
    id: int
    name: str
    is_default: bool = False


class AudioCapture:
    """音频采集器 - 封装麦克风录音和音量检测"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.stream: Optional[sd.InputStream] = None
        self.is_recording = False
        self._audio_callback: Optional[Callable[[np.ndarray], None]] = None
        self._volume_callback: Optional[Callable[[float], None]] = None

    @staticmethod
    def list_devices() -> List[AudioDevice]:
        """列出所有可用输入设备（过滤离线/不可用设备，按名称去重）"""
        devices = sd.query_devices()
        default_idx = sd.default.device[0]
        seen: set[str] = set()
        result = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] <= 0:
                continue
            name = d['name']
            if name in seen:
                continue
            # 尝试验证设备是否真正在线（断开连接的蓝牙等会失败）
            try:
                sd.check_input_settings(device=i, channels=1, samplerate=16000)
            except sd.PortAudioError:
                continue
            seen.add(name)
            result.append(AudioDevice(
                id=i,
                name=name,
                is_default=(i == default_idx)
            ))
        return result

    def start(
        self,
        audio_callback: Callable[[np.ndarray], None],
        volume_callback: Optional[Callable[[float], None]] = None,
        device_id: Optional[int] = None,
    ):
        """开始录音"""
        if self.is_recording:
            return

        self._audio_callback = audio_callback
        self._volume_callback = volume_callback

        def sd_callback(indata, frames, time, status):
            if status:
                logger.warning(f"音频采集状态: {status}")
            volume = float(np.sqrt(np.mean(indata ** 2)))
            if self._volume_callback:
                self._volume_callback(volume)
            if self._audio_callback:
                self._audio_callback(indata.copy())

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            blocksize=1024,
            device=device_id,
            callback=sd_callback,
        )
        self.stream.start()
        self.is_recording = True
        logger.info(f"录音开始 (设备: {device_id or '默认'}, 采样率: {self.sample_rate}Hz)")

    def stop(self):
        """停止录音"""
        if not self.is_recording:
            return

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_recording = False
        self._audio_callback = None
        self._volume_callback = None
        logger.info("录音停止")
