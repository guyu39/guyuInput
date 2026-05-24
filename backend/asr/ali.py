"""
阿里云智能语音交互 (NLS) — WebSocket 流式识别
文档: https://help.aliyun.com/document_detail/84424.html
"""
import json
import logging
import threading
import time
import uuid
import hmac
import hashlib
import base64
from typing import Callable, Optional
from urllib.parse import urlencode, quote

import numpy as np

from .base import ASREngine, ASRResult

logger = logging.getLogger('guyuInput')


class AliASR(ASREngine):
    """阿里云实时语音识别 WebSocket 客户端"""

    TOKEN_URL = "https://nls-meta.cn-shanghai.aliyuncs.com/"
    WS_URL = "wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1"

    def __init__(self, access_key_id: str = "", access_key_secret: str = "", app_key: str = ""):
        super().__init__()
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self._ws = None
        self._is_running = False
        self._thread = None
        self._connected = False
        self._task_id = ""
        self._message_id = ""

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _get_token(self) -> str:
        """通过阿里云 API 签名获取 NLS Token"""
        import urllib.request
        import ssl

        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        nonce = str(uuid.uuid4())

        params = {
            "Action": "CreateToken",
            "Version": "2019-02-28",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "AccessKeyId": self.access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "Timestamp": ts,
            "SignatureNonce": nonce,
        }

        # 1. 排序参数并构建规范化查询字符串
        sorted_keys = sorted(params.keys())
        canonical_qs = "&".join(
            f"{quote(k, safe='')}={quote(params[k], safe='')}" for k in sorted_keys
        )

        # 2. 构造签名原文: GET&%2F& + URL-encoded canonical query string
        string_to_sign = f"GET&{quote('/', safe='')}&{quote(canonical_qs, safe='')}"

        # 3. HMAC-SHA1 签名
        sign = base64.b64encode(hmac.new(
            (self.access_key_secret + "&").encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()).decode("utf-8")

        # 4. 拼接最终 URL
        url = f"{self.TOKEN_URL}?{canonical_qs}&Signature={quote(sign, safe='')}"

        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                tok = data.get("Token", {}).get("Id", "")
                return tok
        except Exception as e:
            logger.warning(f"阿里云获取 Token 失败: {e}")
            return ""

    def _build_url(self) -> str:
        token = self._get_token()
        if not token:
            raise RuntimeError("无法获取阿里云 Token，请检查 AccessKey ID/Secret")
        params = {
            "appkey": self.app_key,
            "token": token,
        }
        return f"{self.WS_URL}?{urlencode(params)}"

    def start(self, on_result: Callable[[ASRResult], None], on_error: Optional[Callable[[str], None]] = None):
        if self._is_running:
            return
        self._on_result = on_result
        self._on_error = on_error
        self._is_running = True
        self._connected = False
        self._task_id = str(uuid.uuid4()).replace("-", "")
        self._message_id = str(uuid.uuid4()).replace("-", "")

        self._thread = threading.Thread(target=self._run_ws, daemon=True)
        self._thread.start()

    def feed_audio(self, audio_data: np.ndarray):
        if not self._connected or not self._ws:
            return
        try:
            pcm = (audio_data * 32767).astype('<i2').tobytes()
            self._ws.send(pcm, opcode=0x2)
        except Exception as e:
            logger.warning(f"阿里发送音频失败: {e}")

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        if self._ws:
            try:
                stop_cmd = json.dumps({
                    "header": {
                        "message_id": str(uuid.uuid4()).replace("-", ""),
                        "task_id": self._task_id,
                        "namespace": "SpeechTranscriber",
                        "name": "StopTranscription",
                        "appkey": self.app_key,
                    },
                    "payload": {}
                })
                self._ws.send(stop_cmd)
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

        try:
            url = self._build_url()
        except RuntimeError as e:
            if self._on_error:
                self._on_error(str(e))
            return

        self._ws = ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_ws_error,
            on_close=self._on_close,
        )
        try:
            ws.run_forever()
        except Exception as e:
            if self._on_error:
                self._on_error(f"阿里 WebSocket 连接失败: {e}")

    def _on_open(self, ws):
        self._connected = True
        # 发送 Start 命令
        start_cmd = json.dumps({
            "header": {
                "message_id": self._message_id,
                "task_id": self._task_id,
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "appkey": self.app_key,
            },
            "payload": {
                "format": "pcm",
                "sample_rate": 16000,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
            }
        })
        ws.send(start_cmd)
        logger.info("阿里 ASR WebSocket 已连接")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        header = data.get("header", {})
        payload = data.get("payload", {})

        name = header.get("name", "")
        status = header.get("status", 0)
        status_text = header.get("status_text", "")

        # 服务端错误事件 (如 TaskFailed)
        if name == "TaskFailed" and self._on_error:
            self._on_error(f"阿里云: {status_text} (状态码: {status})")
            return

        result_text = payload.get("result", "")
        if result_text and self._on_result:
            is_final = (name == "SentenceEnd")
            self._on_result(ASRResult(
                text=result_text,
                is_final=is_final,
                is_partial=not is_final,
            ))

    def _on_ws_error(self, ws, error):
        err_str = str(error)
        # websocket-client 在收到服务端关闭帧时也会调 on_error
        if "opcode=8" in err_str:
            if self._is_running:
                logger.warning(f"阿里 WS 服务端非预期关闭: {err_str}")
                if self._on_error:
                    self._on_error(f"服务端关闭连接: {err_str}")
            else:
                logger.info(f"阿里 WS 服务端关闭: {err_str}")
        else:
            logger.warning(f"阿里 WS 错误: {err_str}")
            if self._on_error:
                self._on_error(err_str)

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info("阿里 ASR WebSocket 已关闭")
        self._connected = False
