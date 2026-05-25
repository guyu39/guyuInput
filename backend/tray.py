"""
系统托盘模块 - Qt 原生 QSystemTrayIcon + QMenu
所有事件在主线程 Qt 事件循环中处理，无需跨线程通信
"""
import logging
from typing import Callable

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap, QIcon, QColor, QPen, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

logger = logging.getLogger('guyuInput')


def _create_tray_icon(size: int = 32) -> QIcon:
    """生成麦克风托盘图标 — 纯矢量绘制，适配高 DPI"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    color = QColor(59, 130, 246)  # blue-500
    pen = QPen(color, 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    r = size / 2
    cx, cy = r, r
    s = size / 24.0

    # 麦克风头部
    from PySide6.QtGui import QPainterPath
    body = QPainterPath()
    body.addRoundedRect(QRectF(cx - 3*s, cy - 6*s, 6*s, 8*s), 3*s, 3*s)
    painter.drawPath(body)

    # 底座弧线
    arc = QPainterPath()
    arc.moveTo(cx - 5*s, cy - 3*s)
    arc.quadTo(cx, cy + 4*s, cx + 5*s, cy - 3*s)
    painter.drawPath(arc)

    # 底部直线 + 横线
    from PySide6.QtCore import QPointF
    painter.drawLine(QPointF(cx, cy + 1*s), QPointF(cx, cy + 4*s))
    painter.drawLine(QPointF(cx - 3*s, cy + 4*s), QPointF(cx + 3*s, cy + 4*s))

    painter.end()
    return QIcon(pixmap)


class SystemTray:
    """Qt 原生系统托盘"""

    def __init__(self):
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._icon: QIcon = _create_tray_icon(64)  # 大尺寸，Qt 会自动缩放

    def setup(self, on_show: Callable, on_settings: Callable, on_quit: Callable):
        """设置托盘图标和右键菜单"""
        self._tray = QSystemTrayIcon(self._icon)
        self._tray.setToolTip("guyuInput 语音输入法")

        # 右键菜单
        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                padding: 4px;
                color: #e2e8f0;
            }
            QMenu::item {
                padding: 6px 28px 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(96, 165, 250, 0.25);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.08);
                margin: 4px 8px;
            }
        """)

        show_action = QAction("显示窗口")
        show_action.triggered.connect(on_show)
        self._menu.addAction(show_action)

        settings_action = QAction("设置")
        settings_action.triggered.connect(on_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()

        quit_action = QAction("退出")
        quit_action.triggered.connect(on_quit)
        self._menu.addAction(quit_action)

        self._tray.setContextMenu(self._menu)

        # 左键激活 → 显示窗口；右键 → 仅显示菜单（不额外触发显示）
        self._tray.activated.connect(
            lambda reason: on_show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )

        self._tray.show()
        logger.info("Qt 系统托盘已启动")

    def stop(self):
        """隐藏并清理托盘"""
        if self._tray:
            self._tray.hide()
            self._tray = None
        if self._menu:
            self._menu.deleteLater()
            self._menu = None
        logger.info("系统托盘已停止")

    def run_in_thread(self):
        """兼容旧 API — Qt 托盘在主线程运行，此方法为空操作"""
        pass
