"""
录音状态条 - 取消 / 波形 / 确认
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QBrush, QPen
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

from .icons import draw_x, draw_check
from .volume_wave import VolumeWave


CANCEL_BG = QColor(239, 68, 68, 40)
CANCEL_HOVER = QColor(239, 68, 68, 80)
CONFIRM_BG = QColor(34, 197, 94, 40)
CONFIRM_HOVER = QColor(34, 197, 94, 80)


class RecordingWidget(QWidget):
    """录音状态条"""

    cancel = Signal()
    confirm = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(300)
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        self._cancel_btn = _CircleButton(draw_x, CANCEL_BG, CANCEL_HOVER)
        self._cancel_btn.clicked.connect(self.cancel.emit)
        layout.addWidget(self._cancel_btn)

        self.wave = VolumeWave()
        layout.addWidget(self.wave, 1)

        self._confirm_btn = _CircleButton(draw_check, CONFIRM_BG, CONFIRM_HOVER)
        self._confirm_btn.clicked.connect(self.confirm.emit)
        layout.addWidget(self._confirm_btn)

        self.setStyleSheet("""
            RecordingWidget {
                background-color: #1e293b;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px;
            }
        """)

    def set_text(self, text: str):
        pass

    def set_engine(self, name: str):
        pass

    def set_volume(self, level: float):
        self.wave.set_volume(level)


class _CircleButton(QPushButton):
    """32×32 圆形按钮 — 半透明红/绿底色"""

    def __init__(self, draw_fn, bg_color, hover_color, parent=None):
        super().__init__(parent)
        self._draw_fn = draw_fn
        self._bg = bg_color
        self._hover_bg = hover_color
        self._hovered = False
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bg = self._hover_bg if self._hovered else self._bg
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        r = self.width() / 2 - 1
        painter.drawEllipse(self.rect().center(), r, r)

        self._draw_fn(painter, self.rect().toRectF(), QColor(255, 255, 255))

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
