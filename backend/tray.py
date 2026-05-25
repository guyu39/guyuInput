"""
系统托盘模块 - Qt 原生 QSystemTrayIcon + QMenu
"""
import logging
from typing import Callable

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPixmap, QIcon, QColor, QPen, QAction, QPainterPath,
)
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

logger = logging.getLogger('guyuInput')


def _create_tray_icon() -> QIcon:
    """生成托盘图标 — 多分辨率渲染，确保所有 DPI 下抗锯齿"""
    icon = QIcon()
    # Windows 托盘标准尺寸: 16×16 (100%), 32×32 (200%), 48×48 (300%)
    for base in (16, 32, 48):
        size = base * 2  # 2x 超采样
        pixmap = QPixmap(size, size)
        pixmap.setDevicePixelRatio(2.0)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        color = QColor(59, 130, 246)
        pen = QPen(color, base / 8.0)  # 笔宽随尺寸缩放
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        cx = cy = size / 2
        s = size / 24.0

        body = QPainterPath()
        body.addRoundedRect(QRectF(cx - 3 * s, cy - 6 * s, 6 * s, 8 * s), 3 * s, 3 * s)
        painter.drawPath(body)

        arc = QPainterPath()
        arc.moveTo(cx - 5 * s, cy - 3 * s)
        arc.quadTo(cx, cy + 4 * s, cx + 5 * s, cy - 3 * s)
        painter.drawPath(arc)

        painter.drawLine(QPointF(cx, cy + 1 * s), QPointF(cx, cy + 4 * s))
        painter.drawLine(QPointF(cx - 3 * s, cy + 4 * s), QPointF(cx + 3 * s, cy + 4 * s))

        painter.end()
        icon.addPixmap(pixmap)

    return icon


class SystemTray:
    """Qt 原生系统托盘"""

    def __init__(self):
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._icon: QIcon = _create_tray_icon()

    def setup(self, on_show: Callable, on_settings: Callable, on_quit: Callable):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("系统托盘不可用")
            return

        self._tray = QSystemTrayIcon(self._icon)
        self._tray.setToolTip("guyuInput 语音输入法")

        self._menu = QMenu()
        self._menu.setWindowFlags(
            self._menu.windowFlags() | Qt.NoDropShadowWindowHint
        )

        show_act = self._menu.addAction("显示窗口")
        show_act.triggered.connect(on_show)

        settings_act = self._menu.addAction("设置")
        settings_act.triggered.connect(on_settings)

        self._menu.addSeparator()

        quit_act = self._menu.addAction("退出")
        quit_act.triggered.connect(on_quit)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(
            lambda r: on_show() if r == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self._tray.show()
        logger.info("Qt 系统托盘已启动")

    def stop(self):
        if self._tray:
            self._tray.hide()
            self._tray = None
        if self._menu:
            self._menu.deleteLater()
            self._menu = None
        logger.info("系统托盘已停止")

    def run_in_thread(self):
        pass
