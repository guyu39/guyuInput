"""
主窗口控制器 - 管理视图切换和窗口属性
"""
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QMouseEvent, QRegion
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget

from .idle_widget import IdleWidget
from .recording_widget import RecordingWidget
from .error_widget import ErrorWidget
from .guide_page import GuidePage
from .settings_page import SettingsPage


class MainWindow(QMainWindow):
    """主窗口 - frameless, always on top, 管理所有子视图"""

    # 向前端 API 暴露的信号
    start_recording_signal = Signal(int)     # device_id
    stop_recording_signal = Signal(bool)     # confirm
    config_signal = Signal(str, str)         # key, value
    credentials_signal = Signal(str, str)    # provider, json
    refresh_devices_signal = Signal()
    quit_signal = Signal()

    def __init__(self):
        super().__init__()

        # 窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 拖拽支持
        self._drag_pos: QPoint | None = None

        # 中心容器
        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        # 视图栈
        self.stack = QStackedWidget(central)
        self.stack.setStyleSheet("background: transparent;")
        self.stack.setGeometry(0, 0, 64, 64)

        # 创建所有视图
        self.idle = IdleWidget()
        self.recording = RecordingWidget()
        self.error = ErrorWidget()
        self.guide = GuidePage()
        self.settings = SettingsPage()

        self.stack.addWidget(self.idle)       # index 0
        self.stack.addWidget(self.recording)  # index 1
        self.stack.addWidget(self.error)      # index 2
        self.stack.addWidget(self.guide)      # index 3
        self.stack.addWidget(self.settings)   # index 4

        # 默认显示 idle
        self.show_idle()

        # 连线
        self._connect_signals()

        # 托盘显示窗口
        self._tray_show_signal = None

    # ================================================================
    # 视图切换 + 窗口自适应
    # ================================================================

    def show_idle(self):
        self.stack.setCurrentWidget(self.idle)
        self._set_window_size(64, 64, circular=True)

    def show_recording(self, engine: str = ""):
        self.recording.set_engine(engine)
        self.recording.set_text("")
        self.recording.set_volume(0.0)
        self.stack.setCurrentWidget(self.recording)
        self._set_window_size(200, 48, circular=False)

    def show_error(self, message: str, auto_dismiss_ms: int = 0):
        self.error.set_message(message)
        self.stack.setCurrentWidget(self.error)
        self._set_window_size(300, 44, circular=False)
        if auto_dismiss_ms > 0:
            QTimer.singleShot(auto_dismiss_ms, self.show_idle)

    def show_guide(self):
        self.guide.reset()
        self.stack.setCurrentWidget(self.guide)
        self._set_window_size(480, 520, circular=False)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings)
        self._set_window_size(480, 580, circular=False)

    def update_volume(self, level: float):
        self.recording.set_volume(level)

    def update_text(self, text: str):
        self.recording.set_text(text)

    def update_engine(self, engine: str):
        self.recording.set_engine(engine)

    def update_device_list(self, devices_json: str):
        self.settings.load_devices(devices_json)

    def update_config_display(self, config_json: str):
        self.settings.load_config(config_json)

    # ================================================================
    # 内部
    # ================================================================

    def _set_window_size(self, w: int, h: int, circular: bool = False):
        self.setMinimumSize(w, h)
        self.setMaximumSize(w, h)
        self.resize(w, h)
        self.stack.setFixedSize(w, h)

        if circular:
            region = QRegion(0, 0, w, h, QRegion.Ellipse)
            self.setMask(region)
        else:
            self.setMask(QRegion())

    def _connect_signals(self):
        self.idle.clicked.connect(lambda: self.start_recording_signal.emit(-1))
        self.idle.settings_requested.connect(self.show_settings)

        self.recording.cancel.connect(lambda: self.stop_recording_signal.emit(False))
        self.recording.confirm.connect(lambda: self.stop_recording_signal.emit(True))

        self.error.dismissed.connect(self.show_idle)

        self.guide.completed.connect(self._on_guide_done)
        self.guide.open_settings.connect(self.show_settings)

        self.settings.closed.connect(self.show_idle)
        self.settings.config_changed.connect(self.config_signal.emit)
        self.settings.credentials_save.connect(self.credentials_signal.emit)
        self.settings.config_changed.connect(
            lambda k, v: self.refresh_devices_signal.emit() if k == "refresh_devices" else None
        )

    def _on_guide_done(self):
        self.config_signal.emit("first_run", "false")
        self.show_idle()

    # ================================================================
    # 窗口拖拽
    # ================================================================

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            if delta.manhattanLength() > 3:
                self.move(self.pos() + delta)
                self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
