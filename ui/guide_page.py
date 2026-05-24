"""
引导页 - 5步首次使用流程
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QProgressBar, QSizePolicy
)

STEPS = [
    ("欢迎使用 guyuInput",
     "Windows 智能语音输入法，通过语音实时转换为文字，\n显著提升您的文本输入效率。",
     "🎤"),
    ("配置语音识别 API",
     "使用在线语音识别需要配置 API 凭证。\n支持讯飞、豆包、阿里、MiniMax 等供应商。",
     "⚙️"),
    ("语音输入",
     "按住快捷键 Ctrl+Alt+V 开始录音，松开自动识别并上屏。\n也可以点击悬浮麦克风图标开始录音。",
     "🎙️"),
    ("键盘输入",
     "支持标准汉语拼音输入。\n使用数字键 1-5 选词，空格键选择首个候选词。",
     "⌨️"),
    ("开始使用",
     "一切就绪！点击下方按钮开始使用 guyuInput。\n您可以随时右键托盘图标打开设置。",
     "🚀"),
]

DARK_BG = "#0f172a"
GLASS_BG = "rgba(15, 23, 42, 0.95)"
BTN_BG = "#2563eb"
BTN_HOVER = "#3b82f6"


class GuidePage(QWidget):
    """引导页 - 5步流程"""

    completed = Signal()
    open_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(480, 520)
        self._step = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, len(STEPS))
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background: #334155;
                border: none;
                margin: 16px 24px 0 24px;
            }}
            QProgressBar::chunk {{
                background: {BTN_BG};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress)

        # 内容区
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {DARK_BG};")
        for i, (title, desc, emoji) in enumerate(STEPS):
            page = self._make_step_page(i, title, desc, emoji)
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)

        # 底部按钮
        btn_row = QWidget()
        btn_row.setStyleSheet(
            f"background: {DARK_BG};"
            f"border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;"
        )
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(24, 0, 24, 20)

        self.skip_btn = QPushButton("跳过引导")
        self.skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #64748b; font-size: 13px;
                border: none; padding: 8px 12px;
            }}
            QPushButton:hover {{ color: #94a3b8; }}
        """)
        self.skip_btn.clicked.connect(self.completed.emit)
        btn_layout.addWidget(self.skip_btn)
        btn_layout.addStretch()

        self.next_btn = QPushButton("下一步")
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BTN_BG}; color: white; font-size: 13px; font-weight: bold;
                border: none; border-radius: 8px; padding: 10px 24px;
            }}
            QPushButton:hover {{ background: {BTN_HOVER}; }}
        """)
        self.next_btn.clicked.connect(self._next)
        btn_layout.addWidget(self.next_btn)

        layout.addWidget(btn_row)

        self.setStyleSheet(f"""
            GuidePage {{
                background: {GLASS_BG};
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 16px;
            }}
        """)

    def _make_step_page(self, index, title, desc, emoji):
        page = QWidget()
        page.setStyleSheet(f"background: {DARK_BG};")
        v = QVBoxLayout(page)
        v.setAlignment(Qt.AlignCenter)

        icon = QLabel(emoji)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 48px; background: transparent;")
        v.addWidget(icon)
        v.addSpacing(20)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: white; font-size: 20px; font-weight: bold; background: transparent;")
        v.addWidget(title_lbl)
        v.addSpacing(12)

        desc_lbl = QLabel(desc)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setMaximumWidth(360)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 14px; line-height: 1.6; background: transparent;")
        v.addWidget(desc_lbl)

        # Step 2: 配置按钮
        if index == 1:
            v.addSpacing(16)
            cfg_btn = QPushButton("前往配置 API")
            cfg_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {BTN_BG}; color: white; font-size: 14px; font-weight: bold;
                    border: none; border-radius: 8px; padding: 12px 24px;
                }}
                QPushButton:hover {{ background: {BTN_HOVER}; }}
            """)
            cfg_btn.clicked.connect(self.open_settings.emit)
            v.addWidget(cfg_btn, 0, Qt.AlignCenter)

        return page

    def _next(self):
        self._step += 1
        if self._step >= len(STEPS):
            self.completed.emit()
            self._step = 0
            self.stack.setCurrentIndex(0)
            self.progress.setValue(0)
            self.next_btn.setText("下一步")
        else:
            self.stack.setCurrentIndex(self._step)
            self.progress.setValue(self._step)
            if self._step == len(STEPS) - 1:
                self.next_btn.setText("开始使用")

    def reset(self):
        self._step = 0
        self.stack.setCurrentIndex(0)
        self.progress.setValue(0)
        self.next_btn.setText("下一步")
