"""
MiniMax 语音识别 — WebSocket 流式识别
文档: https://platform.minimax.chat/document/asr
"""
import json
import logging
import threading
import time
import uuid
from typing import Callable, Optional
from urllib.parse import urlencode

import numpy as np

from .base import ASREngine, ASRResult

logger = logging.getLogger('guyuInput')


class MiniMaxASR(ASREngine):
    """MiniMax 实时语音识别 WebSocket 客户端"""

    WS_URL = "wss://api.minimax.chat/v1/audio/asr"

    def __init__(self, api_key: str = "", group_id: str = ""):
        super().__init__()
        self.api_key = api_key
        self.group_id = group_id
        self._ws = None
        self._is_running = False
        self._thread = None
        self._connected = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self, on_result: Callable[[ASRResult], None], on_error: Optional[Callable[[str], None]] = None):
        if self._is_running:
            return
        self._on_result = on_result
        self._on_error = on_error
        self._is_running = True
        self._connected = False

        self._thread = threading.Thread(target=self._run_ws, daemon=True)
        self._thread.start()

    def feed_audio(self, audio_data: np.ndarray):
        if not self._connected or not self._ws:
            return
        try:
            pcm = (audio_data * 32767).astype('<i2').tobytes()
            self._ws.send(pcm, opcode=0x2)
        except Exception as e:
            logger.warning(f"MiniMax 发送音频失败: {e}")

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        if self._ws:
            try:
                # 发送静默帧结束
                self._ws.send(b"", opcode=0x2)
                time.sleep(0.2)
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False

    def _build_url(self) -> str:
        params = {"model": "speech-01"}
        return f"{self.WS_URL}?{urlencode(params)}"

    def _run_ws(self):
        try:
            import websocket
        except ImportError:
            if self._on_error:
                self._on_error("websocket-client 未安装")
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        self._ws = ws = websocket.WebSocketApp(
            self._build_url(),
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_ws_error,
            on_close=self._on_close,
        )
        try:
            ws.run_forever()
        except Exception as e:
            if self._on_error:
                self._on_error(f"MiniMax WebSocket 连接失败: {e}")

    def _on_open(self, ws):
        self._connected = True
        # 发送识别配置
        config = {
            "type": "config",
            "data": {
                "model": "speech-01",
                "language": "zh",
                "enable_voice_activity_detection": True,
                "enable_partial": True,
            }
        }
        ws.send(json.dumps(config))
        logger.info("MiniMax ASR WebSocket 已连接")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "result":
            result_data = data.get("data", {})
            text = result_data.get("text", "")
            is_final = result_data.get("is_final", False)
            if text and self._on_result:
                self._on_result(ASRResult(
                    text=text,
                    is_final=is_final,
                    is_partial=not is_final,
                ))
        elif msg_type == "error":
            err_msg = data.get("data", {}).get("message", "未知错误")
            logger.warning(f"MiniMax ASR 错误: {err_msg}")
            if self._on_error:
                self._on_error(err_msg)

    def _on_ws_error(self, ws, error):
        logger.warning(f"MiniMax WS 错误: {error}")
        if self._on_error:
            self._on_error(str(error))

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("MiniMax ASR WebSocket 已关闭")
        self._connected = False
