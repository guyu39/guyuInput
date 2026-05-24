# guyuInput Python 版 - 执行步骤

> 本文档为 Python 版本的详细开发执行计划，按顺序逐步实现。
> 每一步完成后标记 ✅，并记录完成时间。

---

## 第一阶段：项目骨架搭建（M1 - 3天）

### Step 1: 初始化 Python 项目结构

**目标**：创建完整的目录结构和基础配置文件

- [ ] 创建项目根目录 `guyuInput-python/`
- [ ] 创建目录结构：
  ```
  guyuInput-python/
  ├── main.py                    # 程序入口
  ├── requirements.txt           # Python 依赖清单
  ├── pyproject.toml             # 项目配置
  ├── .gitignore
  ├── backend/
  │   ├── __init__.py
  │   ├── app.py                 # 主应用类
  │   ├── config.py              # 配置管理
  │   └── logger.py              # 日志模块
  ├── frontend/                  # React 前端（从现有项目复制）
  │   ├── package.json
  │   ├── src/
  │   └── index.html
  └── assets/                    # 静态资源（图标等）
  ```
- [ ] 编写 `requirements.txt` 初始依赖：
  ```
  pywebview>=4.4.1
  sounddevice>=0.4.6
  numpy>=1.26.0
  websocket-client>=1.6.0
  keyboard>=0.13.5
  pystray>=0.19.5
  pillow>=10.0.0
  ```
- [ ] 验证 Python 环境：`python --version` (要求 3.10+)

**验收标准**：目录结构完整，`pip install -r requirements.txt` 成功

---

### Step 2: pywebview 桌面窗口骨架

**目标**：实现最小可运行的桌面窗口应用

- [ ] 编写 `main.py` 入口：
  ```python
  import webview
  import os
  import sys

  def get_frontend_path():
      if getattr(sys, 'frozen', False):
          return os.path.join(sys._MEIPASS, 'frontend', 'index.html')
      return os.path.join(os.path.dirname(__file__), 'frontend', 'dist', 'index.html')

  if __name__ == '__main__':
      window = webview.create_window(
          title='guyuInput',
          url=get_frontend_path(),
          frameless=True,      # 无边框
          transparent=True,    # 透明背景
          always_on_top=True,  # 置顶
          width=64,
          height=64,
          resizable=False,
          minimized=False,
          on_top=True,
      )
      webview.start(debug=True)  # debug=True 开启开发者工具
  ```
- [ ] 从现有 Go 项目复制 `frontend/` 目录
- [ ] 构建前端：`cd frontend && npm install && npm run build`
- [ ] 运行测试：`python main.py`，窗口正常显示

**验收标准**：运行 `python main.py` 弹出 64×64 透明窗口，无报错

---

### Step 3: 前后端通信（JS Bridge）

**目标**：打通 Python 后端与 React 前端的双向通信

- [ ] 在 `backend/app.py` 中定义 API 类：
  ```python
  class API:
      def __init__(self):
          self.window = None

      def set_window(self, window):
          self.window = window

      # ===== 前端可调用的方法 =====
      def ping(self):
          return "pong"

      def get_version(self):
          return "0.1.0"

      # ===== 后端推送到前端 =====
      def emit(self, event_name, data=None):
          """向前端推送事件"""
          if self.window:
              js_code = f"window.dispatchEvent(new CustomEvent('py-{event_name}', {{ detail: {repr(data)} }}))"
              self.window.evaluate_js(js_code)
  ```
- [ ] 修改 `main.py` 注入 API：
  ```python
  api = API()
  window = webview.create_window(
      ...,
      js_api=api,
  )
  api.set_window(window)
  ```
- [ ] 在前端创建 `src/hooks/usePyBridge.ts`：
  ```typescript
  declare const pywebview: {
      api: {
          ping: () => Promise<string>;
          get_version: () => Promise<string>;
      };
  };

  // 监听后端推送的事件
  export function usePyEvent(eventName: string, callback: (data: any) => void) {
      useEffect(() => {
          const handler = (e: any) => callback(e.detail);
          window.addEventListener(`py-${eventName}`, handler);
          return () => window.removeEventListener(`py-${eventName}`, handler);
      }, [eventName, callback]);
  }
  ```
- [ ] 测试双向通信：前端调用 `pywebview.api.ping()` 收到 "pong"

**验收标准**：前端可调用 Python 方法，Python 可向前端推送事件

---

## 第二阶段：语音输入核心（M2 - 3天）

### Step 4: 音频采集模块

**目标**：实现麦克风音频采集和音量检测

- [ ] 创建 `backend/audio.py`：
  ```python
  import sounddevice as sd
  import numpy as np
  from typing import Callable, Optional, List

  class AudioDevice:
      def __init__(self, id: int, name: str, is_default: bool = False):
          self.id = id
          self.name = name
          self.is_default = is_default

  class AudioCapture:
      def __init__(self, sample_rate: int = 16000, channels: int = 1):
          self.sample_rate = sample_rate
          self.channels = channels
          self.stream: Optional[sd.InputStream] = None
          self.is_recording = False
          self._volume_callback: Optional[Callable[[float], None]] = None
          self._audio_callback: Optional[Callable[[np.ndarray], None]] = None

      @staticmethod
      def list_devices() -> List[AudioDevice]:
          """列出所有可用输入设备"""
          devices = sd.query_devices()
          default_idx = sd.default.device[0]  # 默认输入设备
          result = []
          for i, d in enumerate(devices):
              if d['max_input_channels'] > 0:
                  result.append(AudioDevice(
                      id=i,
                      name=d['name'],
                      is_default=(i == default_idx)
                  ))
          return result

      def start(self,
                audio_callback: Callable[[np.ndarray], None],
                volume_callback: Callable[[float], None],
                device_id: Optional[int] = None):
          """开始录音"""
          self._audio_callback = audio_callback
          self._volume_callback = volume_callback

          def sd_callback(indata, frames, time, status):
              volume = float(np.sqrt(np.mean(indata ** 2)))
              if self._volume_callback:
                  self._volume_callback(volume)
              if self._audio_callback:
                  self._audio_callback(indata.copy())

          self.stream = sd.InputStream(
              samplerate=self.sample_rate,
              channels=self.channels,
              dtype='float32',
              blocksize=1024,  # 64ms
              device=device_id,
              callback=sd_callback,
          )
          self.stream.start()
          self.is_recording = True

      def stop(self):
          """停止录音"""
          if self.stream:
              self.stream.stop()
              self.stream.close()
              self.stream = None
          self.is_recording = False
  ```
- [ ] 添加 API 方法：`get_audio_devices()`, `start_recording()`, `stop_recording()`
- [ ] 测试：启动录音，前端能收到音量变化事件

**验收标准**：能列出麦克风设备，录音时音量值 > 0，停止后不再推送

---

### Step 5: 全局快捷键模块

**目标**：实现 `Ctrl+Alt+V` 全局录音快捷键

- [ ] 创建 `backend/hotkey.py`：
  ```python
  import keyboard
  from typing import Callable, Optional

  class HotkeyManager:
      def __init__(self):
          self.hotkey_str: str = "ctrl+alt+v"
          self._is_pressed = False
          self._on_press: Optional[Callable] = None
          self._on_release: Optional[Callable] = None
          self._hook_id = None

      def set_hotkey(self, hotkey_str: str) -> bool:
          """设置新的快捷键，先取消旧的"""
          if self._hook_id:
              keyboard.unhook(self._hook_id)
          self.hotkey_str = hotkey_str
          return self._register_hook()

      def register_callbacks(self, on_press: Callable, on_release: Callable):
          """注册按下/松开回调"""
          self._on_press = on_press
          self._on_release = on_release

      def _register_hook(self) -> bool:
          """注册键盘钩子"""
          parts = set(self.hotkey_str.lower().split("+"))

          def hook_event(e):
              if e.event_type not in ('down', 'up'):
                  return

              # 检查修饰键
              mods = set()
              if 'ctrl' in parts and (keyboard.is_pressed('ctrl') or keyboard.is_pressed('right ctrl')):
                  mods.add('ctrl')
              if 'alt' in parts and (keyboard.is_pressed('alt') or keyboard.is_pressed('right alt')):
                  mods.add('alt')
              if 'shift' in parts and (keyboard.is_pressed('shift') or keyboard.is_pressed('right shift')):
                  mods.add('shift')

              # 剩余的是主按键
              main_keys = parts - mods
              if len(main_keys) != 1:
                  return

              main_key = next(iter(main_keys))
              if e.name.lower() != main_key:
                  return

              # 确保所有修饰键都按下了
              required_mods = parts & {'ctrl', 'alt', 'shift'}
              if mods != required_mods:
                  return

              # 触发回调
              if e.event_type == 'down' and not self._is_pressed:
                  self._is_pressed = True
                  if self._on_press:
                      self._on_press()
              elif e.event_type == 'up' and self._is_pressed:
                  self._is_pressed = False
                  if self._on_release:
                      self._on_release()

          self._hook_id = keyboard.hook(hook_event)
          return True

      @staticmethod
      def validate_hotkey(hotkey_str: str) -> bool:
          """验证快捷键格式是否合法"""
          parts = hotkey_str.lower().split("+")
          if len(parts) < 2:
              return False
          mods = [p for p in parts if p in {'ctrl', 'alt', 'shift', 'win'}]
          if len(mods) == 0 or len(mods) == len(parts):
              return False
          return True
  ```
- [ ] 在 `main.py` 中初始化快捷键，绑定录音开始/停止
- [ ] 测试：按下 Ctrl+Alt+V 开始录音，松开停止

**验收标准**：全局快捷键生效，即使窗口在后台也能响应

---

### Step 6: 讯飞在线 ASR

**目标**：集成讯飞实时语音识别 WebSocket API

- [ ] 创建 `backend/asr/base.py` 定义抽象基类
- [ ] 创建 `backend/asr/xunfei.py` 实现讯飞客户端：
  ```python
  import websocket
  import json
  import hmac
  import hashlib
  import base64
  from datetime import datetime
  from urllib.parse import urlencode
  from typing import Callable, Optional

  class XunfeiASR:
      def __init__(self, app_id: str, api_key: str, api_secret: str):
          self.app_id = app_id
          self.api_key = api_key
          self.api_secret = api_secret
          self.ws: Optional[websocket.WebSocketApp] = None
          self._on_result: Optional[Callable[[str, bool], None]] = None
          self._on_error: Optional[Callable[[str], None]] = None
          self._is_connected = False

      def _build_auth_url(self) -> str:
          """生成鉴权签名 URL"""
          host = "iat-api.xfyun.cn"
          path = "/v2/iat"
          date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

          signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
          hmac_sha256 = hmac.new(
              self.api_secret.encode('utf-8'),
              signature_origin.encode('utf-8'),
              digestmod=hashlib.sha256
          ).digest()
          signature = base64.b64encode(hmac_sha256).decode('utf-8')

          auth_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
          auth = base64.b64encode(auth_origin.encode('utf-8')).decode('utf-8')

          params = {
              "authorization": auth,
              "date": date,
              "host": host
          }
          return f"wss://{host}{path}?{urlencode(params)}"

      def start(self, on_result: Callable[[str, bool], None], on_error: Callable[[str], None]):
          """启动识别"""
          self._on_result = on_result
          self._on_error = on_error

          def on_open(ws):
              self._is_connected = True
              # 发送握手参数
              handshake = {
                  "data": {
                      "status": 0,
                      "format": "audio/L16;rate=16000",
                      "audio": "",
                      "encoding": "raw"
                  }
              }
              ws.send(json.dumps(handshake))

          def on_message(ws, msg):
              data = json.loads(msg)
              if data.get("code") != 0:
                  if self._on_error:
                      self._on_error(f"ASR Error: {data.get('message')}")
                  return

              # 解析识别结果
              result = ""
              is_final = data["data"]["result"]["ws"][0]["cw"][0]["wp"] == "s"  # 简化版
              # 完整解析逻辑...
              if self._on_result:
                  self._on_result(result, is_final)

          self.ws = websocket.WebSocketApp(
              self._build_auth_url(),
              on_open=on_open,
              on_message=on_message,
              on_error=lambda ws, err: self._on_error and self._on_error(str(err)),
          )
          # 在新线程运行
          import threading
          threading.Thread(target=self.ws.run_forever, daemon=True).start()

      def feed_audio(self, audio_data: bytes):
          """送入音频数据"""
          if self._is_connected and self.ws:
              self.ws.send(audio_data, opcode=websocket.ABNF.OPCODE_BINARY)

      def stop(self):
          """停止识别"""
          if self.ws:
              self.ws.close()
              self.ws = None
          self._is_connected = False
  ```
- [ ] 实现音频格式转换（float32 → int16 PCM）
- [ ] 测试：录音后能收到正确的识别文字

**验收标准**：说"你好"，能正确识别出"你好"

---

### Step 7: 文本注入模块

**目标**：将识别的文字输出到当前光标位置

- [ ] 创建 `backend/input.py`：
  ```python
  import ctypes
  from ctypes import wintypes
  import time

  class TextInjector:
      INPUT_KEYBOARD = 1
      KEYEVENTF_UNICODE = 0x0004
      KEYEVENTF_KEYUP = 0x0002

      VK_CONTROL = 0x11
      VK_V = 0x56
      KEYEVENTF_KEYDOWN = 0x0000

      def __init__(self):
          self.user32 = ctypes.windll.user32
          self.kernel32 = ctypes.windll.kernel32

      def _send_unicode_char(self, char_code: int):
          """发送单个 Unicode 字符"""
          class KEYBDINPUT(ctypes.Structure):
              _fields_ = [
                  ("wVk", wintypes.WORD),
                  ("wScan", wintypes.WORD),
                  ("dwFlags", wintypes.DWORD),
                  ("time", wintypes.DWORD),
                  ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
              ]

          class INPUT(ctypes.Structure):
              _fields_ = [
                  ("type", wintypes.DWORD),
                  ("ki", KEYBDINPUT),
              ]

          inputs = (INPUT * 2)()

          # Key Down
          inputs[0].type = self.INPUT_KEYBOARD
          inputs[0].ki.wScan = char_code
          inputs[0].ki.dwFlags = self.KEYEVENTF_UNICODE

          # Key Up
          inputs[1].type = self.INPUT_KEYBOARD
          inputs[1].ki.wScan = char_code
          inputs[1].ki.dwFlags = self.KEYEVENTF_UNICODE | self.KEYEVENTF_KEYUP

          self.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

      def _set_clipboard_text(self, text: str):
          """设置剪贴板文本"""
          CF_UNICODETEXT = 13

          self.user32.OpenClipboard(0)
          self.user32.EmptyClipboard()

          text_data = text.encode('utf-16-le') + b'\x00\x00'
          h_mem = self.kernel32.GlobalAlloc(0x2002, len(text_data))  # GMEM_MOVEABLE | GMEM_ZEROINIT
          p_mem = self.kernel32.GlobalLock(h_mem)
          ctypes.memmove(p_mem, text_data, len(text_data))
          self.kernel32.GlobalUnlock(h_mem)

          self.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
          self.user32.CloseClipboard()

      def _simulate_ctrl_v(self):
          """模拟 Ctrl+V 粘贴"""
          # Ctrl down
          self.user32.keybd_event(self.VK_CONTROL, 0, self.KEYEVENTF_KEYDOWN, 0)
          time.sleep(0.01)
          # V down
          self.user32.keybd_event(self.VK_V, 0, self.KEYEVENTF_KEYDOWN, 0)
          time.sleep(0.01)
          # V up
          self.user32.keybd_event(self.VK_V, 0, self.KEYEVENTF_KEYUP, 0)
          time.sleep(0.01)
          # Ctrl up
          self.user32.keybd_event(self.VK_CONTROL, 0, self.KEYEVENTF_KEYUP, 0)

      def inject_text(self, text: str):
          """注入文本到当前光标位置"""
          if not text:
              return

          if len(text) <= 50:
              # 短文本：逐字符 SendInput
              for ch in text:
                  self._send_unicode_char(ord(ch))
                  time.sleep(0.005)  # 避免过快丢失字符
          else:
              # 长文本：剪贴板 + Ctrl+V
              self._set_clipboard_text(text)
              time.sleep(0.05)
              self._simulate_ctrl_v()
  ```
- [ ] 测试：打开记事本，调用 `inject_text("你好世界")` 能正确输出

**验收标准**：能在记事本中正确注入中英文混合文本

---

## 第三阶段：离线 ASR（M3 - 2天）

### Step 8: FunASR 离线识别

**目标**：集成 FunASR Paraformer 流式离线识别

- [ ] 更新 `requirements.txt` 添加：
  ```
  funasr>=1.0.0
  torch>=2.0.0
  modelscope>=1.9.0
  ```
- [ ] 创建 `backend/asr/funasr_engine.py`：
  ```python
  from funasr import AutoModel
  import numpy as np
  from typing import Callable, Optional

  class FunASREngine:
      def __init__(self, model_name: str = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"):
          self.model_name = model_name
          self.model = None
          self._cache = {}
          self._on_result: Optional[Callable[[str, bool], None]] = None
          self._is_running = False

      def load_model(self):
          """加载模型（延迟加载，加快启动速度）"""
          if self.model is None:
              self.model = AutoModel(
                  model=self.model_name,
                  device="cpu",  # 或 "cuda"
                  disable_pbar=True,
                  disable_log=True,
              )

      def start(self, on_result: Callable[[str, bool], None]):
          """开始识别"""
          self.load_model()
          self._on_result = on_result
          self._cache = {}
          self._is_running = True

      def feed_audio(self, audio_data: np.ndarray):
          """送入音频数据（float32, 16kHz）"""
          if not self._is_running or self.model is None:
              return

          # 流式识别
          res = self.model.generate(
              input=audio_data,
              cache=self._cache,
              is_final=False,
              chunk_size=[0, 10, 5],  # 流式配置
          )

          if res and len(res) > 0:
              text = res[0].get("text", "")
              if text and self._on_result:
                  self._on_result(text, is_final=False)

      def stop(self):
          """停止识别，获取最终结果"""
          if not self._is_running or self.model is None:
              return

          # 发送最后一帧
          res = self.model.generate(
              input=np.zeros(1024, dtype=np.float32),
              cache=self._cache,
              is_final=True,
          )

          if res and len(res) > 0:
              text = res[0].get("text", "")
              if text and self._on_result:
                  self._on_result(text, is_final=True)

          self._is_running = False
          self._cache = {}
  ```
- [ ] 测试离线识别：断网情况下能正确识别简单语音

**验收标准**：不联网也能识别中文，准确率 ≥ 90%

---

### Step 9: ASR 调度器（自动降级）

**目标**：实现在线优先、离线兜底的自动切换逻辑

- [ ] 创建 `backend/asr/dispatcher.py`：
  ```python
  from enum import Enum
  from typing import Optional, Callable
  import numpy as np
  from .xunfei import XunfeiASR
  from .funasr_engine import FunASREngine

  class ASRMode(Enum):
      AUTO = "auto"
      ONLINE = "online"
      OFFLINE = "offline"

  class ASRDispatcher:
      def __init__(self,
                   online_engine: Optional[XunfeiASR] = None,
                   offline_engine: Optional[FunASREngine] = None,
                   mode: ASRMode = ASRMode.AUTO):
          self.online = online_engine
          self.offline = offline_engine
          self.mode = mode
          self.current_engine = None
          self._on_result: Optional[Callable] = None
          self._on_error: Optional[Callable] = None
          self._is_recording = False
          self._online_failed = False

      def set_credentials(self, provider: str, **kwargs):
          """设置 API 凭证"""
          if provider == "xunfei" and self.online:
              self.online.app_id = kwargs.get("app_id", "")
              self.online.api_key = kwargs.get("api_key", "")
              self.online.api_secret = kwargs.get("api_secret", "")

      def has_online_credentials(self) -> bool:
          """检查在线引擎是否已配置凭证"""
          if not self.online:
              return False
          return bool(self.online.app_id and self.online.api_key and self.online.api_secret)

      def start(self, on_result: Callable, on_error: Callable):
          """开始识别"""
          self._on_result = on_result
          self._on_error = on_error
          self._is_recording = True
          self._online_failed = False

          # 选择引擎
          if self.mode == ASRMode.OFFLINE:
              self._start_offline()
          elif self.mode == ASRMode.ONLINE:
              self._try_start_online()
          else:  # AUTO
              if self.has_online_credentials() and not self._online_failed:
                  if not self._try_start_online():
                      self._start_offline()
              else:
                  self._start_offline()

      def _try_start_online(self) -> bool:
          """尝试启动在线引擎，失败返回 False"""
          if not self.online:
              return False
          try:
              self.online.start(self._on_result, self._online_error)
              self.current_engine = "online"
              return True
          except Exception as e:
              self._online_failed = True
              return False

      def _online_error(self, err: str):
          """在线引擎出错，自动降级"""
          if self.current_engine == "online" and self.mode == ASRMode.AUTO:
              self._online_failed = True
              # 切换到离线...

      def _start_offline(self):
          """启动离线引擎"""
          if self.offline:
              self.offline.start(self._on_result)
              self.current_engine = "offline"

      def feed_audio(self, audio_data: np.ndarray):
          """送入音频数据"""
          if not self._is_recording:
              return
          if self.current_engine == "online" and self.online:
              self.online.feed_audio(audio_data)
          elif self.current_engine == "offline" and self.offline:
              self.offline.feed_audio(audio_data)

      def stop(self):
          """停止识别"""
          self._is_recording = False
          if self.current_engine == "online" and self.online:
              self.online.stop()
          elif self.current_engine == "offline" and self.offline:
              self.offline.stop()
          self.current_engine = None
  ```
- [ ] 测试自动降级：断开网络时自动切换到离线识别

**验收标准**：在线模式断网后自动降级到离线，仍能识别

---

## 第四阶段：前端 UI 重构（可与后端并行）

### Step 10: 悬浮窗 UI 重构

**目标**：实现 3 状态 UI（图标/录音/错误）+ 窗口动态大小调整

- [ ] 重写 `frontend/src/components/FloatingBar.tsx`：
  - 状态1：空闲（仅麦克风圆形图标，64×64）
  - 状态2：录音（左✕、中文字+波形、右✓，320×56 可扩展）
  - 状态3：错误提示（红色文字+图标）
- [ ] 实现窗口大小调整 API（Python 端）：
  ```python
  def resize_window(self, width: int, height: int):
      if self.window:
          self.window.resize(width, height)
  ```
- [ ] 前端状态变化时调用后端调整窗口大小
- [ ] 实现 3 秒无语音超时检测（前端或后端）

**验收标准**：点击图标展开录音界面，点击取消/确认后回到图标状态

---

### Step 11: 引导页

**目标**：首次运行 5 步引导流程

- [ ] 创建 `frontend/src/components/GuidePage.tsx`
- [ ] 5步流程：欢迎 → API配置 → 语音说明 → 键盘说明 → 完成
- [ ] Step 2 提供"前往配置"按钮打开设置面板
- [ ] 完成后写入本地配置，下次不再显示

**验收标准**：首次运行显示引导页，完成后下次启动直接进入图标状态

---

### Step 12: 设置面板

**目标**：完整的配置界面

- [ ] 创建 `frontend/src/components/SettingsPanel.tsx`
- [ ] 功能模块：
  - 识别模式切换（自动/仅在线/仅离线）
  - 多供应商 API 配置（讯飞/豆包/阿里/MiniMax）
  - 快捷键录制
  - 麦克风设备选择
  - 词库导入
- [ ] 配置持久化（Python 端 SQLite）

**验收标准**：修改设置后重启程序，配置依然有效

---

## 第五阶段：系统集成与打包（M5 - 2天）

### Step 13: 系统托盘

**目标**：后台运行 + 托盘菜单

- [ ] 创建 `backend/tray.py`：
  ```python
  import pystray
  from PIL import Image
  from typing import Callable

  class SystemTray:
      def __init__(self, icon_path: str):
          self.icon = Image.open(icon_path)
          self._tray = None
          self._on_show: Optional[Callable] = None
          self._on_quit: Optional[Callable] = None

      def setup(self, on_show: Callable, on_quit: Callable):
          """设置回调"""
          self._on_show = on_show
          self._on_quit = on_quit

      def run(self):
          """运行托盘"""
          menu = pystray.Menu(
              pystray.MenuItem("显示窗口", self._on_show),
              pystray.MenuItem("退出", self._on_quit),
          )
          self._tray = pystray.Icon(
              "guyuInput",
              self.icon,
              "guyuInput 语音输入法",
              menu
          )
          self._tray.run()

      def stop(self):
          """停止托盘"""
          if self._tray:
              self._tray.stop()
  ```
- [ ] 在 `main.py` 中集成托盘，在独立线程运行

**验收标准**：关闭窗口后程序在后台运行，托盘菜单可恢复窗口/退出

---

### Step 14: 配置持久化

**目标**：SQLite 存储配置

- [ ] 创建 `backend/config.py`：
  ```python
  import sqlite3
  import os
  import json
  from typing import Any, Optional

  class ConfigManager:
      def __init__(self, db_path: str = None):
          if db_path is None:
              db_path = os.path.join(os.path.expanduser("~"), ".guyuInput", "config.db")
          os.makedirs(os.path.dirname(db_path), exist_ok=True)
          self.conn = sqlite3.connect(db_path)
          self._init_table()

      def _init_table(self):
          self.conn.execute("""
              CREATE TABLE IF NOT EXISTS config (
                  key TEXT PRIMARY KEY,
                  value TEXT
              )
          """)
          self.conn.commit()

      def get(self, key: str, default: str = "") -> str:
          cur = self.conn.execute("SELECT value FROM config WHERE key = ?", (key,))
          row = cur.fetchone()
          return row[0] if row else default

      def set(self, key: str, value: str):
          self.conn.execute(
              "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
              (key, value)
          )
          self.conn.commit()

      def get_bool(self, key: str, default: bool = False) -> bool:
          return self.get(key, str(default)).lower() == "true"

      def get_json(self, key: str, default: Any = None) -> Any:
          val = self.get(key, "")
          if not val:
              return default
          try:
              return json.loads(val)
          except:
              return default

      def set_json(self, key: str, value: Any):
          self.set(key, json.dumps(value, ensure_ascii=False))
  ```
- [ ] 所有配置项通过 ConfigManager 读写

**验收标准**：重启程序后配置不丢失

---

### Step 15: 打包与安装程序

**目标**：生成 Windows 可执行文件和安装包

- [ ] 方案 A：Nuitka 编译（推荐，体积小）
  ```bash
  python -m nuitka \
    --standalone \
    --onefile \
    --windows-disable-console \
    --include-data-dir=frontend/dist=frontend \
    --include-data-dir=assets=assets \
    --enable-plugin=upx \
    main.py
  ```
- [ ] 方案 B：PyInstaller（简单，体积大）
  ```bash
  pyinstaller --onefile --windowed --noconsole main.py
  ```
- [ ] 编写 NSIS 安装脚本 `build/setup.iss`
- [ ] 生成安装包，测试安装/卸载流程

**验收标准**：在干净 Windows 上安装后可正常运行

---

## 第六阶段：测试与优化

### Step 16: 端到端测试

- [ ] 完整流程测试：启动 → 配置API → 快捷键录音 → 文字上屏
- [ ] 离线模式测试：断网后正常识别
- [ ] 异常测试：麦克风被占用、API 过期、网络中断
- [ ] 兼容性测试：Windows 10 / Windows 11，不同 DPI 缩放

### Step 17: 性能优化

- [ ] 启动优化：延迟加载 FunASR 模型（第一次使用离线模式才加载）
- [ ] 内存优化：模型量化，ONNX 格式替代 PyTorch
- [ ] 体积优化：排除不必要的依赖（如 torch 可只留 cpu 版本）
- [ ] 识别延迟优化：调整音频帧大小，优化 ASR 调度逻辑

---

## 执行顺序建议（按依赖关系）

**第一周**：
1. ✅ Step 1: 项目结构
2. ✅ Step 2: pywebview 窗口
3. ✅ Step 3: 前后端通信
4. ✅ Step 4: 音频采集
5. ✅ Step 5: 全局快捷键
6. ✅ Step 7: 文本注入
7. ✅ Step 10: 悬浮窗 UI（此时已有最小可用版本）

**第二周**：
8. Step 6: 讯飞在线 ASR
9. Step 8: FunASR 离线 ASR
10. Step 9: ASR 调度器
11. Step 11: 引导页
12. Step 12: 设置面板
13. Step 13: 系统托盘
14. Step 14: 配置持久化
15. Step 15: 打包

**第三周**：
16. Step 16: 测试
17. Step 17: 优化

---

## 完成标准

每一步完成后，应满足：
- 代码可运行，无报错
- 验收标准全部通过
- 注释清晰，关键逻辑有说明
- 提交 git commit，描述完成内容
