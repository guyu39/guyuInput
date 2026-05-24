"""
图标绘制 - 使用 QPainterPath 绘制矢量图标，不依赖外部 SVG 文件
"""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush
from PySide6.QtWidgets import QWidget


def draw_mic(painter: QPainter, rect: QRectF, color: QColor):
    """麦克风图标"""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    cx, cy = rect.center().x(), rect.center().y()
    s = min(rect.width(), rect.height()) / 24.0

    # 麦克风头部（椭圆）
    body = QPainterPath()
    body.addRoundedRect(QRectF(cx - 3*s, cy - 6*s, 6*s, 8*s), 3*s, 3*s)
    painter.drawPath(body)

    # 底座弧线
    arc = QPainterPath()
    arc.moveTo(cx - 5*s, cy - 3*s)
    arc.quadTo(cx, cy + 4*s, cx + 5*s, cy - 3*s)
    painter.drawPath(arc)

    # 底部直线
    painter.drawLine(QPointF(cx, cy + 1*s), QPointF(cx, cy + 4*s))

    # 底座横线
    painter.drawLine(QPointF(cx - 3*s, cy + 4*s), QPointF(cx + 3*s, cy + 4*s))

    painter.restore()


def draw_x(painter: QPainter, rect: QRectF, color: QColor):
    """X 图标"""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, 2.5)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)

    m = min(rect.width(), rect.height()) * 0.25
    cx, cy = rect.center().x(), rect.center().y()
    painter.drawLine(QPointF(cx - m, cy - m), QPointF(cx + m, cy + m))
    painter.drawLine(QPointF(cx + m, cy - m), QPointF(cx - m, cy + m))

    painter.restore()


def draw_check(painter: QPainter, rect: QRectF, color: QColor):
    """✓ 图标"""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, 2.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    m = min(rect.width(), rect.height()) * 0.25
    cx, cy = rect.center().x(), rect.center().y()
    path = QPainterPath()
    path.moveTo(cx - 0.8*m, cy)
    path.lineTo(cx - 0.2*m, cy + 0.6*m)
    path.lineTo(cx + 0.8*m, cy - 0.5*m)
    painter.drawPath(path)

    painter.restore()


def draw_warning(painter: QPainter, rect: QRectF, color: QColor):
    """警告三角形图标"""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(color, 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    m = min(rect.width(), rect.height()) * 0.3
    cx, cy = rect.center().x(), rect.center().y()

    # 三角形
    tri = QPainterPath()
    tri.moveTo(cx, cy - m)
    tri.lineTo(cx + m, cy + 0.6*m)
    tri.lineTo(cx - m, cy + 0.6*m)
    tri.closeSubpath()
    painter.drawPath(tri)

    # 感叹号竖线
    painter.drawLine(QPointF(cx, cy - 0.2*m), QPointF(cx, cy + 0.2*m))
    # 感叹号圆点
    painter.setBrush(color)
    painter.drawEllipse(QPointF(cx, cy + 0.45*m), 0.08*m, 0.08*m)

    painter.restore()


def draw_gear(painter: QPainter, center: QPointF, radius: float, color: QColor):
    """小齿轮图标 — 外圈+齿+内圆心"""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)

    pen = QPen(color, 1.2)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    cx, cy = center.x(), center.y()

    # 外圈
    painter.drawEllipse(center, radius, radius)

    # 6 个齿（径向短线）
    for i in range(6):
        import math
        angle = i * math.pi / 3
        dx = math.cos(angle)
        dy = math.sin(angle)
        r_inner = radius * 0.6
        painter.drawLine(
            QPointF(cx + dx * r_inner, cy + dy * r_inner),
            QPointF(cx + dx * radius, cy + dy * radius),
        )

    # 内圆心
    painter.setBrush(color)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(center, radius * 0.3, radius * 0.3)

    painter.restore()


class IconButton(QWidget):
    """可绘制图标的圆形按钮"""

    def __init__(self, draw_fn, icon_color=QColor(255, 255, 255),
                 bg_color=QColor(30, 41, 59), hover_color=None,
                 parent=None):
        super().__init__(parent)
        self.draw_fn = draw_fn
        self.icon_color = icon_color
        self.bg_color = bg_color
        self.hover_color = hover_color or bg_color.lighter(130)
        self._hovered = False
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景圆
        bg = self.hover_color if self._hovered else self.bg_color
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        
        # 修复 1：明确使用浮点数，并稍微多留 0.5 像素的边距给抗锯齿
        r = min(self.width(), self.height()) / 2.0 - 1.5 
        
        # 修复 2：使用 QRectF 获取精准的浮点中心点 (20.0, 20.0)
        center_point = QRectF(self.rect()).center()
        
        painter.drawEllipse(center_point, r, r)

        # 图标
        self.draw_fn(painter, QRectF(self.rect()), self.icon_color)
    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
