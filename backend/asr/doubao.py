"""
豆包语音识别 (火山引擎) — WebSocket 流式识别
文档: https://www.volcengine.com/docs/6561/1354868
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


class DoubaoASR(ASREngine):
    """火山引擎实时语音识别 WebSocket 客户端"""

    WS_URL = "wss://openspeech.bytedance.com/api/v2/asr"

    def __init__(self, app_id: str = "", access_token: str = ""):
        super().__init__()
        self.app_id = app_id
        self.access_token = access_token
        self._ws = None
        self._is_running = False
        self._thread = None
        self._connected = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _build_url(self) -> str:
        return self.WS_URL

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
            logger.warning(f"豆包发送音频失败: {e}")

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        if self._ws:
            try:
                end_msg = json.dumps({"type": "End"})
                self._ws.send(end_msg)
                time.sleep(0.2)
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False

    def _run_ws(self):
        try:
            import websocket
        except ImportError:
            if self._on_error:
                self._on_error("websocket-client 未安装")
            return

        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
        }

        self._ws = ws = websocket.WebSocketApp(
            self.WS_URL,
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
                self._on_error(f"豆包 WebSocket 连接失败: {e}")

    def _on_open(self, ws):
        self._connected = True
        # 发送 StartConnection 全参数字段
        start_msg = json.dumps({
            "type": "StartConnection",
            "version": "1.0",
            "payload": {
                "format": "pcm",
                "rate": 16000,
                "bits": 16,
                "channel": 1,
                "language": "zh-CN",
                "enable_punctuation": True,
            }
        })
        ws.send(start_msg)
        logger.info("豆包 ASR WebSocket 已连接")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "RecognitionResult":
            payload = data.get("payload", {})
            result_text = payload.get("result", "")
            is_final = payload.get("is_final", False)

            if result_text and self._on_result:
                self._on_result(ASRResult(
                    text=result_text,
                    is_final=is_final,
                    is_partial=not is_final,
                ))
        elif msg_type == "Error":
            err_msg = data.get("payload", {}).get("message", "未知错误")
            logger.warning(f"豆包 ASR 错误: {err_msg}")
            if self._on_error:
                self._on_error(err_msg)

    def _on_ws_error(self, ws, error):
        logger.warning(f"豆包 WS 错误: {error}")
        if self._on_error:
            self._on_error(str(error))

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("豆包 ASR WebSocket 已关闭")
        self._connected = False
