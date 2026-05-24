"""
主窗口控制器 - 管理视图切换和窗口属性
"""
import ctypes
from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QEvent
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

        # 窗口属性 — 不抢焦点、不激活
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        # 长按拖拽支持
        self._drag_pos: QPoint | None = None
        self._drag_active = False
        QApplication.instance().installEventFilter(self)

        # 焦点激活控制：录音/空闲态禁止，设置/引导页允许
        self._allow_activate = False

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

    def _update_activation(self, allow: bool):
        """统一管理窗口激活：nativeEvent 标志 + Win32 WS_EX_NOACTIVATE 样式"""
        self._allow_activate = allow
        self._set_allow_activate(allow)

    # ================================================================
    # 视图切换 + 窗口自适应
    # ================================================================

    def show_idle(self):
        self._update_activation(False)
        self.stack.setCurrentWidget(self.idle)
        self._set_window_size(64, 64, circular=True)

    def show_recording(self, engine: str = ""):
        self._update_activation(False)
        self.recording.set_engine(engine)
        self.recording.set_text("")
        self.recording.set_volume(0.0)
        self.stack.setCurrentWidget(self.recording)
        self._set_window_size(280, 66, circular=False)

    def show_error(self, message: str, auto_dismiss_ms: int = 0):
        self._update_activation(False)
        self.error.set_message(message)
        self.stack.setCurrentWidget(self.error)
        self._set_window_size(300, 44, circular=False)
        if auto_dismiss_ms > 0:
            QTimer.singleShot(auto_dismiss_ms, self.show_idle)

    def show_guide(self):
        self._update_activation(True)
        self.guide.reset()
        self.stack.setCurrentWidget(self.guide)
        self._set_window_size(480, 520, circular=False)

    def show_settings(self):
        self._update_activation(True)
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

        # Qt 的 setMask / resize 可能覆盖窗口样式，重新加回 WS_EX_NOACTIVATE
        self._apply_ws_ex_noactivate()

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
    # Win32 窗口样式 — 从底层阻止鼠标点击激活窗口
    # ================================================================

    GWL_EXSTYLE = -20
    WS_EX_NOACTIVATE = 0x08000000

    def showEvent(self, event):
        super().showEvent(event)
        hwnd = int(self.winId())
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, self.GWL_EXSTYLE, ex_style | self.WS_EX_NOACTIVATE
        )

    def _apply_ws_ex_noactivate(self):
        """给窗口附加 WS_EX_NOACTIVATE，从 Win32 层面阻止鼠标激活"""
        if not self.isVisible():
            return
        hwnd = int(self.winId())
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, self.GWL_EXSTYLE, ex_style | self.WS_EX_NOACTIVATE
        )

    def _set_allow_activate(self, allow: bool):
        """切换 WS_EX_NOACTIVATE：设置/引导页需要激活才能输入文字"""
        if not self.isVisible():
            return
        hwnd = int(self.winId())
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        if allow:
            ex_style &= ~self.WS_EX_NOACTIVATE
        else:
            ex_style |= self.WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, ex_style)

    # ================================================================
    # 焦点拦截 — 鼠标点击不激活窗口
    # ================================================================

    def nativeEvent(self, event_type, message):
        """拦截 WM_MOUSEACTIVATE，防止点击窗口时抢夺焦点"""
        WM_MOUSEACTIVATE = 0x0021
        MA_NOACTIVATE = 3
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_MOUSEACTIVATE and not self._allow_activate:
                return True, MA_NOACTIVATE
        return False, 0

    # ================================================================
    # 长按拖拽 — 全局事件过滤器，覆盖所有子视图（含录音条、设置页）
    # ================================================================

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype not in (QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.MouseButtonRelease):
            return super().eventFilter(obj, event)

        me = event
        if me.button() != Qt.LeftButton and etype != QEvent.MouseMove:
            return super().eventFilter(obj, event)

        if etype == QEvent.MouseButtonPress:
            self._drag_pos = me.globalPosition().toPoint()
            self._drag_active = False

        elif etype == QEvent.MouseMove and self._drag_pos is not None:
            if not self._drag_active:
                delta = me.globalPosition().toPoint() - self._drag_pos
                if delta.manhattanLength() < 5:
                    return super().eventFilter(obj, event)
                self._drag_active = True
            delta = me.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = me.globalPosition().toPoint()
            return True  # 消费事件，阻止子控件响应

        elif etype == QEvent.MouseButtonRelease:
            was_drag = self._drag_active
            self._drag_pos = None
            self._drag_active = False
            if was_drag:
                return True  # 拖拽结束后吞掉 click

        return super().eventFilter(obj, event)
