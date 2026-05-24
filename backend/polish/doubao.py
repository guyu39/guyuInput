"""豆包 (火山引擎 ark) 润色器"""
import json
import logging
import socket
import urllib.request
import urllib.error

from .base import BasePolisher, PolishMode
from .prompts import get_prompt

logger = logging.getLogger('guyuInput')

_DEFAULT_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
_DEFAULT_TIMEOUT = 30  # 秒（LLM 推理可能需要较长时间）


class DoubaoPolisher(BasePolisher):
    """豆包大模型润色器"""

    def __init__(self, api_key: str, model: str = "doubao-pro-32k",
                 endpoint: str = _DEFAULT_ENDPOINT, timeout: int = _DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    def polish(self, text: str, mode: PolishMode) -> str:
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": get_prompt(text, mode)},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)  # 连接超时 10s
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            logger.error(f"豆包 API HTTP {e.code}: {body_text}")
            raise RuntimeError(f"API 请求失败 (HTTP {e.code})")
        except urllib.error.URLError as e:
            logger.error(f"豆包 API 网络错误: {e.reason}")
            raise RuntimeError(f"网络请求失败: {e.reason}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"豆包 API 响应解析失败: {e}")
            raise RuntimeError("API 响应格式异常")
        except TimeoutError:
            logger.error(f"豆包 API 超时 ({self.timeout}s)")
            raise RuntimeError(f"API 请求超时 ({self.timeout}s)")
        finally:
            socket.setdefaulttimeout(old_timeout)
