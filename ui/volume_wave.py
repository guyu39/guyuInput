"""
音量波形组件 - 绘制跳动的音量条
"""
import math
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtWidgets import QWidget


class VolumeWave(QWidget):
    """5段音量波形指示器"""

    BAR_COUNT = 5
    BASE_HEIGHT = 4
    MAX_ADD = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 0.0
        self.setFixedSize(20, 20)

    def set_volume(self, level: float):
        """设置音量 0.0 ~ 1.0+"""
        self._volume = min(level, 1.5)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bar_w = 3
        gap = 2
        total_w = self.BAR_COUNT * bar_w + (self.BAR_COUNT - 1) * gap
        start_x = (self.width() - total_w) / 2

        for i in range(self.BAR_COUNT):
            phase = 1 + 0.5 * (self._volume > 0.01 and math.sin(i * 0.8))
            h = self.BASE_HEIGHT + self._volume * self.MAX_ADD * phase
            h = min(h, self.height())

            x = start_x + i * (bar_w + gap)
            y = self.height() - h

            painter.setBrush(QBrush(QColor(96, 165, 250)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_w, h), 1.5, 1.5)
