# guyuInput Python 版 - 需求分析文档

## 1. 项目概述

### 1.1 项目背景

guyuInput 是一款 Windows 平台的智能语音输入法，通过将语音实时转换为文字，提升用户的文本输入效率。

**技术选型变更说明**：原 Go + Wails 方案因开发效率和离线 ASR 生态限制，重构为 Python 后端 + React 前端架构。

### 1.2 核心目标

- **高识别准确率**：在线识别 ≥ 95%，离线识别 ≥ 92%
- **低延迟响应**：首字出字 < 300ms，整句延迟 < 1s
- **轻量体积**：安装包 ≤ 50MB，内存占用 ≤ 100MB（空闲）
- **无缝体验**：类似主流输入法的悬浮窗形态，不干扰用户正常操作

---

## 2. 功能需求

### 2.1 核心功能

#### 2.1.1 语音输入（P0）

| 需求项 | 说明 | 优先级 |
|--------|------|--------|
| 实时语音识别 | 按住快捷键开始录音，松开自动识别并上屏 | P0 |
| 流式边说边出字 | 识别过程中实时显示中间结果，提升体感速度 | P0 |
| 音量可视化 | 录音时显示音量波形动画，反馈麦克风工作状态 | P0 |
| 录音状态控制 | 左侧 ✕ 取消，右侧 ✓ 确认，中间显示识别文字 | P0 |
| 无语音自动关闭 | 3秒未检测到有效语音自动提示并关闭录音窗口 | P0 |

#### 2.1.2 拼音输入（P1）

| 需求项 | 说明 | 优先级 |
|--------|------|--------|
| 全拼输入 | 支持标准汉语拼音输入 | P1 |
| 候选词选择 | 1-5 数字键选词，空格选首词 | P1 |
| 动态调频 | 根据用户选择调整候选词排序 | P2 |

#### 2.1.3 识别模式切换（P0）

| 模式 | 说明 | 优先级 |
|------|------|--------|
| 仅在线 | 强制使用云端 API，准确率最高 | P0 |
| 仅离线 | 纯本地识别，无网络依赖，隐私安全 | P0 |
| 自动切换 | 在线优先，网络异常时自动降级到离线 | P0 |

---

### 2.2 配置功能（P0）

#### 2.2.1 多供应商 API 支持

| 供应商 | 接口类型 | 必填字段 |
|--------|----------|----------|
| 讯飞 | WebSocket 流式 | App ID、API Key、API Secret |
| 豆包 | HTTP/WS | App ID、Access Token |
| 阿里 | WebSocket 流式 | AccessKey ID、AccessKey Secret、App Key |
| MiniMax | HTTP/WS | API Key、Group ID |

#### 2.2.2 快捷键配置

- 默认快捷键：`Ctrl + Alt + V`
- 支持用户自定义录制新的快捷键组合
- 快捷键冲突检测与提示

#### 2.2.3 音频设备管理

- 枚举系统所有可用麦克风设备
- 支持选择指定录音设备
- 默认设备自动选择

#### 2.2.4 词库管理

- 基础系统词库（内置）
- 用户词库（自动学习用户输入习惯）
- 自定义词库导入（TXT/CSV 格式）

---

### 2.3 系统集成功能（P0）

| 功能 | 说明 |
|------|------|
| 系统托盘 | 后台运行，托盘图标管理 |
| 开机自启 | 可选，随系统自动启动 |
| 窗口置顶 | 悬浮窗始终在最上层，不被遮挡 |
| 引导页 | 首次运行时的使用指引 + API 配置提示 |
| 错误提示 | Toast 通知，友好的错误反馈 |

---

## 3. 非功能需求

### 3.1 性能指标

| 指标 | 目标值 | 备注 |
|------|--------|------|
| 启动时间 | < 2s | 从点击图标到悬浮窗可见 |
| 响应延迟 | < 200ms | 按键按下到开始录音 |
| 识别延迟 | < 300ms | 录音结束到文字上屏 |
| 内存占用（空闲） | < 80MB | 仅Python进程 + WebView2 |
| 内存占用（录音中） | < 150MB | 含音频处理+ASR引擎 |
| CPU占用（录音中） | < 15% | 4核CPU基准 |
| 安装包体积 | < 50MB | Nuitka 编译后 |

### 3.2 兼容性

- **操作系统**：Windows 10 1809+ / Windows 11（WebView2 预装）
- **DPI 适配**：支持 100%-200% 缩放
- **高DPI感知**：Per-Monitor DPI Aware

### 3.3 安全性

- API 凭证加密存储（Windows DPAPI）
- 录音数据不落地（内存处理，不写入磁盘）
- 无网络时离线模式不发送任何数据

---

## 4. 技术方案（Python 版）

### 4.1 整体架构

```
┌─────────────────────────────────────────────────┐
│                  桌面层                          │
│  pywebview (WebView2) + React 前端              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 悬浮录音窗 │  │ 候选词窗 │  │ 设置面板 │    │
│  └────────────┘  └──────────┘  └──────────┘    │
└──────────────────┬──────────────────────────────┘
                   │ JS Bridge
┌──────────────────▼──────────────────────────────┐
│               Python 后端                       │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐    │
│  │  音频采集 │  │ ASR 调度 │  │  文本注入  │    │
│  │(sddevice)│  │(多引擎)  │  │ (SendInput)│    │
│  └──────────┘  └──────────┘  └────────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐    │
│  │ 快捷键监听│  │ 配置管理 │  │  系统托盘  │    │
│  │(keyboard)│  │(sqlite)  │  │ (pystray)  │    │
│  └──────────┘  └──────────┘  └────────────┘    │
└─────────────────────────────────────────────────┘
```

### 4.2 后端技术栈

| 模块 | 技术选型 | 说明 |
|------|----------|------|
| 桌面窗口 | **pywebview** | 嵌入系统 WebView2，支持透明无边框窗口 |
| 音频采集 | **sounddevice** | PortAudio 封装，WASAPI 低延迟，Windows 预编译 wheel |
| 在线 ASR | **websocket-client** | 讯飞/阿里 流式 WebSocket 协议 |
| 离线 ASR | **FunASR (Paraformer)** | 达摩院开源，中文识别准确率高，支持流式 |
| 文本注入 | **ctypes (标准库)** | 直接调用 Win32 SendInput，Unicode 逐字符输入 |
| 全局快捷键 | **keyboard** | WH_KEYBOARD_LL 钩子，支持 press/release 事件 |
| 配置存储 | **sqlite3 + json** | 内置 SQLite，无需额外依赖 |
| 系统托盘 | **pystray** | 跨平台托盘图标，支持右键菜单 |
| 日志 | **logging (标准库)** | 按大小滚动的日志文件 |

### 4.3 前端技术栈（复用现有代码）

| 模块 | 技术选型 |
|------|----------|
| 框架 | React 18 + TypeScript |
| 构建工具 | Vite 5.x |
| 样式 | TailwindCSS 4.x |
| 状态管理 | Zustand |
| 通信方式 | pywebview JS Bridge |

### 4.4 打包方案

- **开发阶段**：Vite dev server + pywebview 加载本地 URL
- **生产阶段**：Vite build → pywebview 加载本地 HTML → **Nuitka** 编译为原生 exe
- **安装包**：NSIS 制作安装程序

---

## 5. 核心模块详细设计

### 5.1 音频采集模块

**关键参数**：
- 采样率：16000 Hz
- 声道：单声道
- 位深：16bit / float32
- 帧长：64ms（1024 samples）

**核心逻辑**：
```python
import sounddevice as sd
import numpy as np

class AudioCapture:
    def __init__(self, device_id=None, sample_rate=16000):
        self.sample_rate = sample_rate
        self.device_id = device_id
        self.stream = None
        self.is_recording = False

    def start(self, callback):
        """启动录音，callback 接收 (audio_data, volume)"""
        def sd_callback(indata, frames, time, status):
            volume = float(np.sqrt(np.mean(indata**2)))
            callback(indata.copy(), volume)

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=1024,
            device=self.device_id,
            callback=sd_callback,
        )
        self.stream.start()
        self.is_recording = True

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.is_recording = False

    @staticmethod
    def list_devices():
        """返回可用输入设备列表"""
        devices = sd.query_devices()
        return [
            {"id": i, "name": d["name"], "is_default": False}
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        ]
```

### 5.2 ASR 调度模块

**接口定义**：

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class ASRMode(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AUTO = "auto"

@dataclass
class ASRResult:
    text: str
    is_final: bool
    is_partial: bool

class ASREngine(ABC):
    @abstractmethod
    def start(self, callback):
        """启动识别，callback(result: ASRResult)"""

    @abstractmethod
    def feed_audio(self, audio_data: np.ndarray):
        """送入音频数据"""

    @abstractmethod
    def stop(self):
        """停止识别，触发 final 结果"""

class ASRDispatcher:
    def __init__(self, online_engine, offline_engine, mode=ASRMode.AUTO):
        self.online = online_engine
        self.offline = offline_engine
        self.mode = mode
        self.current_engine = None

    def start_recognition(self, callback):
        """根据模式选择引擎，自动降级"""
        if self.mode == ASRMode.ONLINE:
            self._try_online(callback)
        elif self.mode == ASRMode.OFFLINE:
            self._start_offline(callback)
        else:  # AUTO
            if not self._try_online(callback):
                self._start_offline(callback)
```

### 5.3 快捷键监听模块

```python
import keyboard

class HotkeyManager:
    def __init__(self):
        self.hotkey = "ctrl+alt+v"
        self.is_pressed = False
        self.on_press_cb = None
        self.on_release_cb = None

    def register(self, hotkey_str, on_press, on_release):
        """注册录音快捷键，分离按下/松开回调"""
        self.hotkey = hotkey_str
        self.on_press_cb = on_press
        self.on_release_cb = on_release

        # 解析组合键
        parts = set(hotkey_str.lower().split("+"))

        def hook(e):
            required = parts.copy()
            pressed = set()

            if "ctrl" in required and keyboard.is_pressed("ctrl"):
                pressed.add("ctrl")
                required.remove("ctrl")
            if "alt" in required and keyboard.is_pressed("alt"):
                pressed.add("alt")
                required.remove("alt")
            if "shift" in required and keyboard.is_pressed("shift"):
                pressed.add("shift")
                required.remove("shift")

            # 检查主按键
            if e.name in required and len(required) == 1:
                if e.event_type == "down" and not self.is_pressed:
                    self.is_pressed = True
                    if self.on_press_cb:
                        self.on_press_cb()
                elif e.event_type == "up" and self.is_pressed:
                    self.is_pressed = False
                    if self.on_release_cb:
                        self.on_release_cb()

        keyboard.hook(hook)

    @staticmethod
    def parse_hotkey(hotkey_str):
        """验证快捷键格式合法性"""
        parts = hotkey_str.lower().split("+")
        modifiers = {"ctrl", "alt", "shift", "win"}
        mod_count = sum(1 for p in parts if p in modifiers)
        if mod_count == 0 or mod_count == len(parts):
            raise ValueError("快捷键需要至少一个修饰键 + 一个普通键")
        return True
```

### 5.4 文本注入模块

```python
import ctypes
from ctypes import wintypes

class TextInjector:
    """SendInput Unicode 文本注入"""

    INPUT_KEYBOARD = 1
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def inject_text(self, text: str):
        """注入文本到当前光标位置"""
        if len(text) <= 50:
            # 短文本：逐字符 SendInput
            for ch in text:
                self._send_unicode_char(ord(ch))
        else:
            # 长文本：剪贴板 + Ctrl+V
            self._set_clipboard_text(text)
            self._simulate_ctrl_v()

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
```

---

## 6. 前端 UI 设计

### 6.1 悬浮录音窗

#### 状态流转

```
首次启动 → 引导页（5步）→ 完成引导 → 仅显示语音图标（空闲状态）
                                                         ↓
                                                点击 icon / 按快捷键
                                                         ↓
                                                ┌───────────────┐
                                                │  录音/识别中  │
                                                └───────┬───────┘
                                                        │
                              ┌─────────────────────────┼─────────────────────────┐
                              ↓                         ↓                         ↓
                        点击 ✕ 取消               点击 ✓ 确认输入         3秒无语音超时
                              │                         │                         │
                              ▼                         ▼                         ▼
                        关闭窗口，丢弃内容       输出文字到光标处           提示后自动关闭
```

---

#### 状态1：首次启动 - 引导页

- **触发条件**：程序首次运行
- **窗口尺寸**：480 × 520 px（完整窗口）
- **内容**：5步引导流程
  1. 欢迎使用
  2. 配置语音 API（必须项，提供快捷跳转设置按钮）
  3. 语音输入说明
  4. 键盘输入说明
  5. 开始使用
- **交互**：支持跳过，跳过或完成后自动收缩为语音图标

---

#### 状态2：空闲状态（仅语音图标）

- **窗口尺寸**：64 × 64 px（紧凑圆形）
- **视觉样式**：
  - 深色调圆形背景：`#1e293b`
  - 蓝色麦克风 SVG 图标
  - 轻微阴影与边框
  - 悬停效果：背景微亮 + 图标高亮
- **交互**：
  - ✅ 左键点击 → 进入录音状态
  - ✅ 快捷键 `Ctrl+Alt+V` → 进入录音状态
  - ✅ 鼠标拖拽 → 调整窗口位置
  - ✅ 右键菜单 → 打开设置 / 退出程序

---

#### 状态3：录音 / 识别状态

**窗口尺寸**：动态自适应（初始 320 × 56 px，内容多时向四周扩展）

**布局结构**：

```
  左固定区        中间弹性区（可扩展）        右固定区
┌─────────┬──────────────────────────────────┬─────────┐
│         │                                  │         │
│  [✕]    │   识别文字内容...  音量波形      │   [✓]   │
│         │                                  │         │
└─────────┴──────────────────────────────────┴─────────┘
    ↓                       ↓                       ↓
  40x40 px             自适应宽度               40x40 px
红色半透明背景      文字多时自动向两侧扩展    绿色半透明背景
```

**详细样式**：

| 区域 | 样式描述 |
|------|----------|
| **左侧 - 取消按钮** | 40×40 px 圆形，红色半透明背景 `rgba(239,68,68,0.15)`，白色 ✕ 图标，悬停背景加深 |
| **中间 - 识别内容区** | 弹性宽度，文字左对齐，白色 14px，溢出时显示省略号；内容增加时窗口向左右两侧扩展（最大宽度 500px）；录音时显示音量波形动画，识别中显示跳动圆点 |
| **右侧 - 确认按钮** | 40×40 px 圆形，绿色半透明背景 `rgba(34,197,94,0.15)`，白色 ✓ 图标，悬停背景加深 |

**交互行为**：
- ✅ 点击左侧 ✕ → 取消本次录音，关闭窗口，回到图标状态
- ✅ 点击右侧 ✓ → 停止识别，将文字输出到当前光标位置，然后关闭窗口
- ✅ 3秒未检测到有效语音 → 中间区域显示"未检测到语音，即将关闭"提示，1.5秒后自动关闭
- ✅ 出现错误时 → 中间区域显示错误信息（红色文字），可点击关闭

**动态扩展规则**：
- 初始宽度：320 px
- 文字内容增加时：保持按钮位置不动，容器向两侧同步扩展
- 最大宽度：500 px
- 文字超长：截断 + 省略号，hover 显示完整 tooltip

---

#### 状态4：错误提示

- **显示位置**：中间内容区
- **样式**：红色文字 + 警告图标
- **场景**：API 调用失败、麦克风权限被占用、音频设备断开等
- **恢复**：用户可点击取消关闭，或3秒后自动关闭

### 6.2 引导页流程

```
Step 1: 欢迎使用 → Step 2: 配置语音 API → Step 3: 语音输入说明
                                                 ↓
                                          Step 4: 键盘输入说明
                                                 ↓
                                          Step 5: 开始使用
```

关键交互：Step 2 提供"前往配置 API"按钮，打开设置面板

### 6.3 设置面板

**语音识别模式**
- 单选按钮组：自动切换 / 仅在线 / 仅离线

**多供应商 API 配置**
- Tab 切换：讯飞 / 豆包 / 阿里 / MiniMax
- 每个供应商：状态指示（已配置/未配置）+ 凭证字段 + 保存按钮

**快捷键配置**
- 显示当前快捷键 + "录制新快捷键"按钮
- 录制状态："按下组合键..."

**麦克风设备**
- 下拉选择框，显示所有可用输入设备

---

## 7. 开发计划

### 7.1 里程碑

| 阶段 | 周期 | 交付内容 |
|------|------|----------|
| M1：核心骨架 | 3天 | Python + pywebview 框架、窗口系统、前后端通信打通 |
| M2：语音输入 | 3天 | 音频采集 + 讯飞在线 ASR + 文本注入 + 快捷键 |
| M3：离线 ASR | 2天 | FunASR 集成 + 自动降级调度 |
| M4：拼音输入 | 2天 | 拼音引擎 + 候选词窗 |
| M5：配置与系统集成 | 2天 | 设置面板 + 系统托盘 + 引导页 + 打包 |
| **总计** | **~12天** | |

### 7.2 目录结构规划

```
guyuInput-python/
├── main.py                    # 入口文件
├── requirements.txt           # Python 依赖
│
├── backend/
│   ├── __init__.py
│   ├── audio.py              # 音频采集 (sounddevice)
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── base.py           # ASR 引擎抽象基类
│   │   ├── dispatcher.py     # 调度器（在线/离线/自动）
│   │   ├── xunfei.py         # 讯飞在线 ASR
│   │   └── funasr_engine.py  # FunASR 离线 ASR
│   ├── input.py              # 文本注入 (SendInput)
│   ├── hotkey.py             # 快捷键监听 (keyboard)
│   ├── config.py             # 配置管理 (sqlite)
│   └── tray.py               # 系统托盘 (pystray)
│
├── frontend/                  # 复用现有 React 代码
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── stores/
│   │   └── main.tsx
│   └── package.json
│
└── build/                     # 打包脚本
    ├── setup.iss             # NSIS 安装脚本
    └── build_exe.py          # Nuitka 编译脚本
```

---

## 8. 风险与应对

| 风险 | 影响 | 概率 | 应对方案 |
|------|------|------|----------|
| Python 启动慢（>2s） | 高 | 中 | 1. Nuitka 编译优化；2. 延迟加载重型模块（如 FunASR 按需加载） |
| 打包体积过大（>50MB） | 中 | 高 | 1. 排除 PyTorch，FunASR 用 ONNX 版本；2. UPX 压缩 |
| 离线识别准确率低 | 高 | 中 | 1. 采用 FunASR Paraformer 大模型；2. 标点恢复后处理 |
| 快捷键与其他应用冲突 | 中 | 高 | 1. 提供自定义快捷键；2. 冲突检测提示用户 |
| Windows 安全软件拦截 | 高 | 中 | 1. 代码签名（可选）；2. 提供白名单说明 |
| pywebview 窗口问题 | 中 | 中 | 1. 备选方案：pyside6 + QWebEngine；2. 透明窗口降级方案 |

---

## 9. 对比原 Go 方案

| 维度 | Go + Wails（原方案） | Python + pywebview（新方案） |
|------|---------------------|-----------------------------|
| 启动速度 | < 100ms | ~1-2s（可优化到 ~800ms） |
| 内存占用（空闲） | ~20MB | ~60-80MB |
| 安装包体积 | ~25MB | ~40-50MB |
| 离线 ASR 集成难度 | 高（CGo 调用 Sherpa-ONNX） | 低（FunASR 直接 pip 安装） |
| 离线识别准确率 | 中（Sherpa-ONNX） | 高（FunASR Paraformer） |
| 开发调试效率 | 中 | 高（Python 生态 + 热重载） |
| 第三方库生态 | 一般 | 丰富（ASR/ML 领域首选） |
| 代码复用率 | - | 前端代码 100% 复用 |

**核心优势变更**：
- ✅ 获得：更好的离线识别效果、更快的开发速度、更丰富的 ML 生态
- ❌ 放弃：极快启动、极小体积

**适用场景判断**：对于语音输入法这类 AI 驱动的产品，**识别准确率和开发效率优先级高于 1 秒启动时间**。Python 方案在核心体验（识别质量）上有明显优势。
