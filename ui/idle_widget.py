"""
空闲状态 - 64×64 圆形麦克风图标
"""
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QRegion, QMouseEvent
from PySide6.QtWidgets import QWidget

from .icons import draw_mic


class IdleWidget(QWidget):
    """圆形悬浮麦克风按钮"""

    clicked = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("左键录音  |  右键打开设置")
        self._hovered = False
        self._drag_pos: QPoint | None = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景圆
        bg = QColor(51, 65, 85) if self._hovered else QColor(30, 41, 59)  # #334155 : #1e293b
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(QColor(255, 255, 255, 25), 1))  # border-white/10
        r = self.width() / 2 - 2
        painter.drawEllipse(self.rect().center(), r, r)

        # 麦克风图标
        draw_mic(painter, self.rect().toRectF(), QColor(96, 165, 250))  # blue-400

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.RightButton:
            self.settings_requested.emit()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self._drag_pos is not None:
                delta = event.globalPosition().toPoint() - self._drag_pos
                if delta.manhattanLength() < 5:
                    self.clicked.emit()
            self._drag_pos = None

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            if delta.manhattanLength() > 3:
                # 拖拽窗口
                self.window().move(
                    self.window().pos() +
                    (event.globalPosition().toPoint() - self._drag_pos)
                )
                self._drag_pos = event.globalPosition().toPoint()
