"""OpenAI 及兼容 API 润色器"""
import json
import logging
import socket
import urllib.request
import urllib.error

from .base import BasePolisher, PolishMode
from .prompts import get_prompt

logger = logging.getLogger('guyuInput')

_DEFAULT_TIMEOUT = 30  # 秒（LLM 推理可能需要较长时间）


class OpenAIPolisher(BasePolisher):
    """OpenAI / 兼容 API (DeepSeek, 通义千问, Moonshot 等)"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini", timeout: int = _DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def polish(self, text: str, mode: PolishMode) -> str:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": get_prompt(text, mode)},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        req = urllib.request.Request(
            url,
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
            logger.error(f"OpenAI API HTTP {e.code}: {body_text}")
            raise RuntimeError(f"API 请求失败 (HTTP {e.code})")
        except urllib.error.URLError as e:
            logger.error(f"OpenAI API 网络错误: {e.reason}")
            raise RuntimeError(f"网络请求失败: {e.reason}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"OpenAI API 响应解析失败: {e}")
            raise RuntimeError("API 响应格式异常")
        except TimeoutError:
            logger.error(f"OpenAI API 超时 ({self.timeout}s)")
            raise RuntimeError(f"API 请求超时 ({self.timeout}s)")
        finally:
            socket.setdefaulttimeout(old_timeout)
