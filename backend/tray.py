"""
系统托盘模块 - 基于 pystray 的托盘图标和菜单
"""
import logging
import threading
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger('guyuInput')


def _create_icon_image(size: int = 32) -> Image.Image:
    """生成麦克风托盘图标"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 6
    r = (size - 2 * margin) // 2
    cx, cy = size // 2, size // 2

    # 麦克风主体（椭圆）
    body_top = margin
    body_bottom = cy - r // 3
    body_left = cx - r // 2
    body_right = cx + r // 2
    draw.rounded_rectangle(
        [body_left, body_top, body_right, body_bottom],
        radius=size // 8,
        fill=(59, 130, 246)  # blue-500
    )

    # 底座弧线
    arc_bbox = [cx - r, cy - r // 3, cx + r, cy + r]
    draw.arc(arc_bbox, start=0, end=180, fill=(59, 130, 246), width=size // 8)

    return img


class SystemTray:
    """系统托盘管理"""

    def __init__(self):
        self._tray: Optional[pystray.Icon] = None
        self._on_show: Optional[Callable] = None
        self._on_quit: Optional[Callable] = None
        self._running = False

    def setup(self, on_show: Callable, on_quit: Callable):
        """设置回调"""
        self._on_show = on_show
        self._on_quit = on_quit

    def run(self):
        """启动托盘（阻塞）"""
        if self._running:
            return

        image = _create_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem(
                "显示窗口",
                self._handle_show,
                default=True,
            ),
            pystray.MenuItem(
                "关于",
                self._handle_about,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "退出",
                self._handle_quit,
            ),
        )

        self._tray = pystray.Icon(
            "guyuInput",
            image,
            "guyuInput 语音输入法",
            menu,
        )
        self._running = True
        logger.info("系统托盘启动")
        self._tray.run()

    def run_in_thread(self):
        """在独立线程中启动托盘"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def stop(self):
        """停止托盘"""
        self._running = False
        if self._tray:
            self._tray.stop()
            self._tray = None
        logger.info("系统托盘已停止")

    def _handle_show(self):
        if self._on_show:
            self._tray and self._on_show()

    def _handle_about(self):
        if self._tray:
            self._tray.notify("guyuInput v0.1.0\nWindows 智能语音输入法")

    def _handle_quit(self):
        self.stop()
        if self._on_quit:
            self._on_quit()
