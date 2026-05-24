# guyuInput Qt 方案需求分析

## 1. 变更范围

```
┌──────────────────┬──────────────────┬──────────────────────┐
│      模块        │      状态        │        说明          │
├──────────────────┼──────────────────┼──────────────────────┤
│ backend/audio.py │      保留        │ 零改动               │
│ backend/asr/     │      保留        │ 零改动               │
│ backend/hotkey.py│      保留        │ 零改动               │
│ backend/input.py │      保留        │ 零改动               │
│ backend/config.py│      保留        │ 零改动               │
│ backend/tray.py  │      保留        │ 零改动               │
│ backend/logger.py│      保留        │ 零改动               │
│ backend/app.py   │   重写为 ui/     │ API 类拆分            │
│ main.py          │      重写        │ pywebview → Qt        │
│ frontend/        │    全部删除      │ React 不再需要        │
│ requirements.txt │    增删依赖      │ pywebview→PySide6     │
└──────────────────┴──────────────────┴──────────────────────┘
```

## 2. 架构对比

```
        原方案                              Qt 方案
┌──────────────────────┐           ┌──────────────────────┐
│   pywebview 窗口     │           │   Qt 原生窗口        │
│   ┌──────────────┐   │           │   (QWidget)          │
│   │  WebView2    │   │           │   ┌──────────────┐   │
│   │  ┌────────┐  │   │           │   │  Qt 控件     │   │
│   │  │ React   │  │   │           │   │  (QLabel,    │   │
│   │  │ 前端    │  │   │           │   │   QPushBtn)  │   │
│   │  └────────┘  │   │           │   └──────────────┘   │
│   └──────────────┘   │           │                      │
│         ↕ JS Bridge   │           │        ↕ 信号/槽      │
│   ┌──────────────┐   │           │   ┌──────────────┐   │
│   │  API 类      │   │           │   │  后端模块    │   │
│   └──────────────┘   │           │   │  (不变)      │   │
└──────────────────────┘           └──────────────────────┘
```

## 3. UI 状态对照

### 3.1 空闲状态 (64×64 圆形)

| 要素 | React 写法 | Qt 实现 |
|------|-----------|---------|
| 窗口尺寸 | `resize_window(64, 64)` | `self.resize(64, 64)` / `setFixedSize(64, 64)` |
| 圆形裁剪 | `rounded-full` CSS | `setMask(QRegion(0,0,64,64, QRegion.Ellipse))` |
| 背景色 | `bg-[#1e293b]` | `QPalette` 或 QSS |
| 麦克风图标 | SVG 组件 | QPainter 绘制 或 QSvgWidget |
| 悬停效果 | `hover:bg-[#334155]` | `enterEvent` / `leaveEvent` |
| 左键点击 | `onClick` | `mousePressEvent` → 开始录音 |
| 右键菜单 | `onContextMenu` | `contextMenuEvent` → 打开设置 |

### 3.2 录音状态 (320×56 → 500×56)

```
┌────────┬──────────────────────────────┬────────┐
│   ✕    │   识别文字...     ▏▃▅▇       │   ✓    │
│ 40×40  │        弹性宽度               │ 40×40  │
│ 红底   │    文字 + 波形               │ 绿底   │
└────────┴──────────────────────────────┴────────┘
```

| 要素 | Qt 实现 |
|------|---------|
| 窗口横向扩展 | `self.setMinimumWidth(320); self.setMaximumWidth(500)` |
| 取消按钮 | `QPushButton` 40×40, stylesheet 红底 |
| 文字区 | `QLabel`, `setWordWrap(True)`, 弹性宽度 |
| 音量波形 | 继承 `QWidget`, 重写 `paintEvent`, QTimer 刷新 |
| 确认按钮 | `QPushButton` 40×40, stylesheet 绿底 |
| 文字超长 | QLabel 自动省略号 + tooltip |

### 3.3 错误 / 超时提示

| 要素 | Qt 实现 |
|------|---------|
| 图标 + 文字 + 关闭按钮 | QHBoxLayout 水平排列 |
| 红色边框 | QSS `border: 1px solid rgba(239,68,68,0.3)` |
| 3秒自动关闭 | QTimer.singleShot |

### 3.4 引导页 (480×520)

| 要素 | Qt 实现 |
|------|---------|
| 5步流程 | `QStackedWidget` 切换页面 |
| 进度条 | `QProgressBar` 动态更新 |
| 步骤内容 | 每步一个 `QWidget`，含图标(QLabel emoji)、标题、描述 |
| 按钮 | `QPushButton` "下一步" / "跳过引导" |
| 配置按钮 | Step 2 的按钮切换到设置面板 |

### 3.5 设置面板 (480×520)

| 要素 | Qt 实现 |
|------|---------|
| 标题栏 | 水平布局 + 关闭按钮 |
| Tab 切换 | `QTabWidget` (ASR / 快捷键 / 音频设备) |
| 单选按钮组 | `QButtonGroup` + `QRadioButton` |
| 凭证输入 | `QLineEdit` (密码模式) |
| 供应商切换 | `QComboBox` 或 水平按钮组 |
| 快捷键录制 | `QLineEdit` + `QPushButton`, `keyPressEvent` 捕获 |
| 设备下拉 | `QComboBox` 列出音频设备 |

## 4. 通信方式对比

```
原方案 (JS Bridge):               Qt 方案 (Signal/Slot):
                                  
前端调用 Python:                  前端调用 Python:
  pywebview.api.method()      →    直接调用对象方法 (同进程)
                                  
Python 推送前端:                  Python 推送 UI:
  window.evaluate_js(         →    signal.emit(data)
    "dispatchEvent(...)")                 ↓
                                 QLabel.setText(), etc.
```

Qt 优势：同进程直接调用，无序列化，无跨语言桥接。

## 5. 文件规划

```
ui/                          ← 新增，取代 frontend/
├── __init__.py
├── main_window.py           ← 主窗口控制器 (QStackedWidget 管理视图)
├── idle_widget.py           ← 空闲圆形图标
├── recording_widget.py      ← 录音状态条
├── error_widget.py          ← 错误/超时提示
├── volume_wave.py           ← 音量波形绘制
├── guide_page.py            ← 引导页 (5步)
├── settings_page.py         ← 设置面板
└── icons.py                 ← SVG → QPainter 路径绘制
```

## 6. 依赖变更

```diff
# requirements.txt
- pywebview>=4.4.1
+ PySide6>=6.6.0

# 删除
- frontend/ (React/TypeScript/TailwindCSS/Node.js 全部不再需要)
- main.py (重写)

# 保留不变
  sounddevice, numpy, websocket-client
  keyboard, pystray, pillow
  sqlite3 (标准库)
```

安装包体积：PySide6 ≈ 80MB（远大于 pywebview 的~5MB），但你说内存不用考虑。

## 7. 工作量估算

| 模块 | 工时 | 说明 |
|------|------|------|
| idle_widget.py | 0.5天 | 圆形窗口 + 图标绘制 |
| recording_widget.py | 1天 | 水平条 + 波形 + 文字 |
| error_widget.py | 0.3天 | 简单水平布局 |
| volume_wave.py | 0.3天 | paintEvent 绘制 |
| guide_page.py | 0.5天 | 5 步 QStackedWidget |
| settings_page.py | 1天 | 3 Tab + 表单 |
| icons.py | 0.3天 | 几个 SVG 路径 |
| main_window.py | 0.5天 | 视图切换 + 信号路由 |
| main.py 重写 | 0.3天 | Qt 启动 + 托盘集成 |
| 后端适配 (app.py) | 0.3天 | JS emit → Qt signal |
| **合计** | **~5天** | 删除前端后净增 ~207 行配置 |

## 8. 风险

| 风险 | 等级 | 应对 |
|------|------|------|
| PySide6 体积大 (~80MB) | 低 | 用户明确说不在意 |
| Qt 样式调校耗时 | 中 | QSS 接近 CSS，经验可迁移 |
| pystray 与 Qt 事件循环冲突 | 中 | pystray 已在独立线程运行，不受影响 |

## 9. 结论

- **删掉** frontend/ 全部 React/TypeScript/Node.js 代码
- **删掉** pywebview 依赖
- **新增** ui/ 目录，用 PySide6 原生控件重建 5 个 UI 组件
- **后端** audio/asr/hotkey/input/config/tray → 全部零改动
- 透明窗口问题从根源消失（Qt 原生 `WA_TranslucentBackground`）
