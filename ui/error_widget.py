"""
错误/超时提示条
"""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from .icons import draw_warning, draw_x


class ErrorWidget(QWidget):
    """错误提示条"""

    dismissed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)

        # 警告图标
        icon = _PaintLabel(draw_warning, QColor(248, 113, 113), 20)  # red-400
        icon.setFixedSize(20, 20)
        layout.addWidget(icon)

        # 消息
        self.msg_label = QLabel()
        self.msg_label.setStyleSheet("color: #fca5a5; font-size: 13px; background: transparent;")
        self.msg_label.setWordWrap(True)
        self.msg_label.setMaximumWidth(360)
        layout.addWidget(self.msg_label, 1)

        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.2);
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(239,68,68,0.4);
            }
        """)
        close_btn.clicked.connect(self.dismissed.emit)
        layout.addWidget(close_btn)

        self.setStyleSheet("""
            ErrorWidget {
                background-color: #1e293b;
                border: 1px solid rgba(239,68,68,0.3);
                border-radius: 12px;
            }
        """)

    def set_message(self, text: str):
        self.msg_label.setText(text)

    @staticmethod
    def show_silence_timeout(title="未检测到语音，即将关闭"):
        """显示超时提示"""
        w = ErrorWidget()
        w.set_message(title)
        QTimer.singleShot(2000, w.dismissed.emit)
        return w


class _PaintLabel(QWidget):
    """可绘制图标的标签"""

    def __init__(self, draw_fn, color, size, parent=None):
        super().__init__(parent)
        self._draw_fn = draw_fn
        self._color = color
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        self._draw_fn(painter, self.rect().toRectF(), self._color)
