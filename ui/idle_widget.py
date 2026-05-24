"""
空闲状态 - 64×64 圆形麦克风图标
右上角有关闭按钮，点击隐藏到托盘
"""
from PySide6.QtCore import Qt, QPoint, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QMouseEvent
from PySide6.QtWidgets import QWidget

from .icons import draw_mic, draw_x

# 关闭按钮 — 圆外右上角，避开麦克风图标和圆形区域
# 圆形半径 30，中心 (32,32)，右上边缘约 (53,11)；按钮放在 (55,10) 确保在圆外
CLOSE_BTN_CX = 55
CLOSE_BTN_CY = 10
CLOSE_BTN_R = 6


class IdleWidget(QWidget):
    """圆形悬浮麦克风按钮"""

    clicked = Signal()
    settings_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("左键录音  |  右键设置  |  右上 X 隐藏到托盘")
        self._hovered = False
        self._close_hovered = False
        self._press_pos: QPoint | None = None
        self._close_pressed = False

    def _close_rect(self) -> QRectF:
        """关闭按钮的矩形区域"""
        return QRectF(CLOSE_BTN_CX - CLOSE_BTN_R, CLOSE_BTN_CY - CLOSE_BTN_R,
                      CLOSE_BTN_R * 2, CLOSE_BTN_R * 2)

    def _hit_close(self, pos: QPoint) -> bool:
        """判断坐标是否在关闭按钮区域内"""
        dx = pos.x() - CLOSE_BTN_CX
        dy = pos.y() - CLOSE_BTN_CY
        return (dx * dx + dy * dy) <= (CLOSE_BTN_R * CLOSE_BTN_R)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景圆 - 毛玻璃暗底
        if self._hovered:
            bg = QColor(30, 41, 59, 245)
        else:
            bg = QColor(15, 23, 42, 235)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))  # border-white/12
        
        # 修复 2：使用浮点除法并转为 QRectF，防止坐标截断导致整个图形向左上角偏移 1 像素
        r = self.width() / 2.0 - 2.0
        center_point = QRectF(self.rect()).center()
        
        painter.drawEllipse(center_point, r, r)

        # 麦克风图标
        draw_mic(painter, QRectF(self.rect()), QColor(96, 165, 250))  # blue-400

        # 关闭按钮 ×
        close_color = QColor(239, 68, 68) if self._close_hovered else QColor(148, 163, 184, 100)
        draw_x(painter, self._close_rect(), close_color)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self._close_hovered = False
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        self._close_hovered = self._hit_close(pos)
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        if event.button() == Qt.LeftButton:
            if self._hit_close(pos):
                self._close_pressed = True
                return
            self._press_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.RightButton:
            self.settings_requested.emit()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self._close_pressed:
                self._close_pressed = False
                pos = event.position().toPoint()
                if self._hit_close(pos):
                    self.close_requested.emit()
                    return
            if self._press_pos is not None:
                delta = event.globalPosition().toPoint() - self._press_pos
                if delta.manhattanLength() < 5:
                    self.clicked.emit()
        self._press_pos = None
