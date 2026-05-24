# guyuInput

Windows 智能语音输入法 — 按住说话，松开识别，文字自动注入到任意应用。

## 功能特性

- **按住说话**：全局热键（默认 `Ctrl+Alt+V`），按住录音，松开识别并注入文本
- **在线/离线双模式**：在线接入讯飞/阿里/豆包/MiniMax API，离线使用本地 sherpa-onnx SenseVoice 模型
- **自动降级**：网络异常时自动切换到离线识别
- **系统托盘**：最小化到托盘，右键菜单快速访问设置和退出
- **多音频设备**：支持选择任意输入设备
- **悬浮窗口**：半透明毛玻璃 UI，不抢焦点，不打断当前工作

## 技术栈

| 模块 | 技术 |
|------|------|
| UI 框架 | PySide6 (Qt) — 悬浮毛玻璃窗口 |
| 音频采集 | sounddevice — 16kHz 单声道 |
| 在线 ASR | 讯飞 / 阿里云 NLS / 豆包 / MiniMax WebSocket |
| 离线 ASR | sherpa-onnx + SenseVoice INT8 模型 |
| 文本注入 | Win32 API (剪贴板 + 模拟 Ctrl+V) |
| 快捷键 | keyboard 库全局钩子 |
| 系统托盘 | pystray + PIL |

## 项目结构

```
guyuInput/
├── main.py                  # 入口，连线 API ↔ UI
├── backend/
│   ├── app.py               # API 核心，Qt 信号通信
│   ├── audio.py             # 音频采集 (sounddevice)
│   ├── hotkey.py            # 全局快捷键管理
│   ├── input.py             # 文本注入 (Win32)
│   ├── tray.py              # 系统托盘 (pystray)
│   ├── config.py            # SQLite 配置管理
│   ├── logger.py            # 日志初始化
│   └── asr/
│       ├── base.py           # ASR 引擎抽象接口
│       ├── dispatcher.py     # 在线/离线调度器 + 自动降级
│       ├── sherpa_onnx_engine.py  # 离线引擎 (sherpa-onnx)
│       ├── xunfei.py         # 讯飞实时语音转写
│       ├── ali.py            # 阿里云 NLS
│       ├── doubao.py         # 豆包语音识别
│       └── minimax.py        # MiniMax ASR
├── ui/
│   ├── main_window.py       # 主窗口控制器 + 视图切换
│   ├── idle_widget.py       # 空闲态：圆形麦克风图标
│   ├── recording_widget.py  # 录音态：文字回显 + 取消/确认
│   ├── error_widget.py      # 错误提示条
│   ├── guide_page.py        # 首次引导页
│   ├── settings_page.py     # 设置页 (API 凭证/设备/快捷键)
│   └── icons.py             # 矢量图标绘制
└── models/                   # 离线模型（需单独下载）
    ├── model.int8.onnx       # SenseVoice INT8 (~239MB)
    └── tokens.txt            # 词表
```

## 安装

### 1. 环境要求

- Windows 10/11 x64
- Python 3.12+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载离线模型（可选）

不使用离线识别可跳过。模型文件约 240MB：

```bash
mkdir models
# 从 Hugging Face 镜像下载
curl -L "https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx" -o models/model.int8.onnx
curl -L "https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt" -o models/tokens.txt
```

### 4. 运行

```bash
python main.py
```

首次运行会弹出引导页，可选择配置在线 API 凭证或直接使用离线模式。

## 使用说明

| 操作 | 方式 |
|------|------|
| 开始录音 | 按住 `Ctrl+Alt+V`（可在设置中修改） |
| 取消录音 | 松开热键后点击录音条左侧 ✕ |
| 确认注入 | 松开热键后点击录音条右侧 ✓（或直接松开即自动注入） |
| 隐藏到托盘 | 点击麦克风图标右上角 ✕ |
| 显示窗口 | 系统托盘左键 / 双击托盘图标 |
| 打开设置 | 系统托盘右键 → 设置 |
| 退出程序 | 系统托盘右键 → 退出 |

## 配置说明

### ASR 模式

- **自动**（默认）：优先在线，网络异常自动切离线
- **仅在线**：只使用指定供应商 API
- **仅离线**：始终使用本地 sherpa-onnx 模型

### 在线供应商

| 供应商 | 需要配置的凭证 |
|--------|---------------|
| 讯飞 | App ID + API Key + API Secret |
| 阿里云 | AccessKey ID + Secret + App Key |【已实现】
| 豆包 | App ID + Access Token |
| MiniMax | API Key + Group ID |

凭证保存在本地 SQLite 数据库 (`config.db`)。

### 快捷键

默认 `Ctrl+Alt+V`，支持任意组合键（如 `ctrl+shift+a`、`alt+r`）。

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 仅在线模式（无需下载模型）
python main.py

# 验证离线引擎
python -c "
from backend.asr import SherpaOnnxEngine
import numpy as np
e = SherpaOnnxEngine()
e.start(on_result=lambda r: print(r.text))
e.feed_audio(np.zeros(16000, dtype=np.float32))
e.stop()
"
```

## 开源引用

本项目使用了以下开源项目，按其各自许可证分发：

| 项目 | 用途 | 许可证 | 链接 |
|------|------|--------|------|
| sherpa-onnx | 离线语音识别引擎 | Apache 2.0 | https://github.com/k2-fsa/sherpa-onnx |
| SenseVoice | 离线 ASR 模型 | Apache 2.0 | https://github.com/FunAudioLLM/SenseVoice |
| PySide6 | Qt UI 框架 | LGPL 3.0 | https://www.qt.io |
| sounddevice | 音频采集 | MIT | https://github.com/spatialaudio/python-sounddevice |
| keyboard | 全局快捷键 | MIT | https://github.com/boppreh/keyboard |
| pystray | 系统托盘 | LGPL 3.0 | https://github.com/moses-palmer/pystray |
| silero-vad | 语音活动检测 | MIT | https://github.com/snakers4/silero-vad |

本项目原创部分包括：
- 产品设计、交互逻辑与 UI 实现（[ui/](ui/) 目录下所有组件）
- 多供应商 ASR 调度器与自动降级策略（[backend/asr/dispatcher.py](backend/asr/dispatcher.py)）
- 各在线 ASR 供应商的 WebSocket 客户端实现（[backend/asr/](backend/asr/) 下 xunfei / ali / doubao / minimax）
- Win32 文本注入模块（[backend/input.py](backend/input.py)）
- 音频采集封装与音量检测（[backend/audio.py](backend/audio.py)）
- 全局快捷键管理与注入抑制（[backend/hotkey.py](backend/hotkey.py)）
- Qt 窗口管理、视图切换与拖拽支持（[ui/main_window.py](ui/main_window.py)）
- SQLite 配置管理（[backend/config.py](backend/config.py)）
