"""
录音状态条 - 取消 / 文字回显 / 确认
文字增多时窗口高度平滑展开，避免硬切变
"""
from PySide6.QtCore import Qt, Signal, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QBrush
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QTextEdit

from .icons import draw_x, draw_check


CANCEL_COLOR = QColor(239, 68, 68)
CONFIRM_COLOR = QColor(34, 197, 94)

TEXT_MAX_LINES = 3
LINE_HEIGHT = 18
ANIM_DURATION = 180  # ms
ANIM_MIN_DELTA = 2    # 高度差小于此值跳过动画


class RecordingWidget(QWidget):
    """录音状态条 — 带高度展开动画"""

    cancel = Signal()
    confirm = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(360)
        self._volume = 0.0
        self._height_anim: QVariantAnimation | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self._cancel_btn = _IconButton(draw_x, CANCEL_COLOR)
        self._cancel_btn.setFocusPolicy(Qt.NoFocus)
        self._cancel_btn.clicked.connect(self.cancel.emit)
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignVCenter)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFocusPolicy(Qt.NoFocus)
        self._text_edit.setAlignment(Qt.AlignCenter)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._text_edit.setFrameShape(QTextEdit.NoFrame)
        self._text_edit.setStyleSheet(
            "color: #f1f5f9; font-size: 14px;"
            "background-color: rgba(15, 23, 42, 0.5);"
            "border-radius: 8px;"
            "selection-background-color: transparent; padding: 4px 8px;"
        )
        self._text_edit.document().setDocumentMargin(0)
        self._text_edit.setTabChangesFocus(False)
        layout.addWidget(self._text_edit, 1)

        self._confirm_btn = _IconButton(draw_check, CONFIRM_COLOR)
        self._confirm_btn.setFocusPolicy(Qt.NoFocus)
        self._confirm_btn.clicked.connect(self.confirm.emit)
        layout.addWidget(self._confirm_btn, alignment=Qt.AlignVCenter)

        self._fit_height()
        self.setStyleSheet("""
            RecordingWidget {
                background-color: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 12px;
            }
        """)

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)
        sb = self._text_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
        self._fit_height()

    def set_engine(self, name: str):
        pass

    def set_volume(self, level: float):
        self._volume = min(level, 1.5)
        self.update()

    def _fit_height(self):
        doc = self._text_edit.document()
        doc.setTextWidth(self._text_edit.viewport().width() or 180)
        content_h = int(doc.size().height())
        line_count = max(1, content_h // LINE_HEIGHT)
        visible_lines = min(line_count, TEXT_MAX_LINES)
        h = max(48, 12 + visible_lines * LINE_HEIGHT + 4)
        self._animate_height(h)

    # ----------------------------------------------------------------
    # 高度展开动画
    # ----------------------------------------------------------------

    def _animate_height(self, target_h: int):
        current_h = self.height()
        if abs(current_h - target_h) < ANIM_MIN_DELTA:
            self.setFixedHeight(target_h)
            self._sync_window_height(target_h)
            return

        if self._height_anim and self._height_anim.state() == QVariantAnimation.Running:
            self._height_anim.stop()

        self._height_anim = QVariantAnimation(self)
        self._height_anim.setDuration(ANIM_DURATION)
        self._height_anim.setStartValue(current_h)
        self._height_anim.setEndValue(target_h)
        self._height_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._height_anim.valueChanged.connect(self._on_anim_tick)
        self._height_anim.start()

    def _on_anim_tick(self, value):
        h = int(value)
        self.setFixedHeight(h)
        self._sync_window_height(h)

    def _sync_window_height(self, h: int):
        """同步主窗口和视图栈高度，让窗口跟随录音条平滑伸缩"""
        win = self.window()
        if not win:
            return
        # 录音条高度 = 窗口高度（stack 无 margin），同步 resize
        win.resize(win.width(), h)
        # 视图栈也需同步，否则子 widget 被裁剪
        if hasattr(win, 'stack'):
            win.stack.setFixedHeight(h)

    # ----------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_height()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._volume < 0.01:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = int(self.width() * min(self._volume / 0.8, 1.0))
        h = 2
        x = (self.width() - w) // 2
        y = self.height() - 3
        color = QColor(
            min(255, int(self._volume * 100 + 55)),
            200 - int(self._volume * 60),
            55,
        )
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, w, h, 1, 1)


class _IconButton(QPushButton):
    """图标按钮 — 无背景填充，仅图标 + hover 微弱光圈"""

    def __init__(self, draw_fn, color, parent=None):
        super().__init__(parent)
        self._draw_fn = draw_fn
        self._color = color
        self._hovered = False
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._hovered:
            painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
            painter.setPen(Qt.NoPen)
            r = self.width() / 2 - 1
            painter.drawEllipse(self.rect().center(), r, r)

        self._draw_fn(painter, self.rect().toRectF(), self._color)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
