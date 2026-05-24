"""
讯飞语音识别 (WebSocket 流式)
文档: https://www.xfyun.cn/doc/asr/voicedictation/API.html
"""
import logging
import json
import base64
import hashlib
import hmac
import threading
import time
from typing import Callable, Optional
from urllib.parse import urlencode

import numpy as np

from .base import ASREngine, ASRResult

logger = logging.getLogger('guyuInput')


class XunfeiASR(ASREngine):
    """讯飞实时语音识别 WebSocket 客户端"""

    HOST = "iat-api.xfyun.cn"
    PATH = "/v2/iat"
    BASE_URL = f"wss://{HOST}{PATH}"

    def __init__(self, app_id: str = "", api_key: str = "", api_secret: str = ""):
        super().__init__()
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self._ws: Optional[object] = None
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    # 英文常量，避免中文 Windows strftime 输出中文
    _WDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    _MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def _build_url(self) -> str:
        """生成带鉴权签名的 WebSocket URL"""
        now = time.gmtime()
        date = (f"{self._WDAYS[now.tm_wday]}, {now.tm_mday:02d} "
                f"{self._MONTHS[now.tm_mon - 1]} {now.tm_year} "
                f"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d} GMT")

        signature_origin = f"host: {self.HOST}\ndate: {date}\nGET {self.PATH} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode('utf-8')

        auth_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        auth = base64.b64encode(auth_origin.encode('utf-8')).decode('utf-8')

        params = {
            "authorization": auth,
            "date": date,
            "host": self.HOST,
        }
        return f"{self.BASE_URL}?{urlencode(params)}"

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
            # float32 → int16 PCM
            pcm = (audio_data * 32767).astype('<i2').tobytes()
            self._ws.send(pcm, opcode=0x2)  # BINARY
        except Exception as e:
            logger.warning(f"发送音频失败: {e}")

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False
        if self._ws:
            try:
                # 发送结束帧
                end_msg = json.dumps({"data": {"status": 2, "format": "audio/L16;rate=16000", "audio": "", "encoding": "raw"}})
                self._ws.send(end_msg)
                time.sleep(0.2)
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False

    def _run_ws(self):
        """在独立线程中运行 WebSocket 连接"""
        try:
            import websocket
        except ImportError:
            if self._on_error:
                self._on_error("websocket-client 未安装")
            return

        try:
            self._ws = ws = websocket.WebSocketApp(
                self._build_url(),
                header={"Host": self.HOST},
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_ws_error,
                on_close=self._on_close,
            )
            ws.run_forever()
        except Exception as e:
            if self._on_error:
                self._on_error(f"WebSocket 连接失败: {e}")

    def _on_open(self, ws):
        logger.info("讯飞 ASR WebSocket 已连接")
        self._connected = True

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        code = data.get('code')
        if code != 0:
            err_msg = data.get('message', '未知错误')
            logger.warning(f"讯飞 ASR 返回错误: {code} {err_msg}")
            if self._on_error:
                self._on_error(f"[{code}] {err_msg}")
            return

        payload = data.get('data', {}).get('result', {})
        text = self._parse_result(payload)
        status = data.get('data', {}).get('status', 1)

        if text and self._on_result:
            self._on_result(ASRResult(text=text, is_final=(status == 2), is_partial=(status != 2)))

    def _on_ws_error(self, ws, error):
        logger.warning(f"讯飞 WS 错误: {error}")
        if self._on_error:
            self._on_error(str(error))

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("讯飞 ASR WebSocket 已关闭")
        self._connected = False

    @staticmethod
    def _parse_result(result: dict) -> str:
        """解析讯飞识别结果 JSON"""
        text_parts = []
        ws = result.get('ws', [])
        for w in ws:
            cw = w.get('cw', [])
            for c in cw:
                w_text = c.get('w', '')
                if w_text:
                    text_parts.append(w_text)
        return ''.join(text_parts)
