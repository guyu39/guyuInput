"""
文本注入模块 - 统一使用剪贴板 + Ctrl+V，兼容性最广
"""
import ctypes
import time
import logging
from ctypes import wintypes

logger = logging.getLogger('guyuInput')

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

VK_CONTROL = 0x11
VK_V = 0x56
# 标准美式键盘扫描码
SC_CTRL = 0x1D
SC_V = 0x2F


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),  # ULONG_PTR，非 POINTER
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", _KEYBDINPUT),
    ]


class TextInjector:
    """文本注入器 - 剪贴板 + Ctrl+V"""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

        # 修复 x64 参数/返回值类型：默认 c_int 只有 32 位，指针是 64 位
        self.kernel32.GlobalAlloc.restype = ctypes.c_void_p
        self.kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]

        self.kernel32.GlobalLock.restype = ctypes.c_void_p
        self.kernel32.GlobalLock.argtypes = [ctypes.c_void_p]

        self.kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

        self.user32.OpenClipboard.argtypes = [ctypes.c_void_p]  # HWND

        self.user32.GetClipboardData.restype = ctypes.c_void_p
        self.user32.GetClipboardData.argtypes = [wintypes.UINT]

        self.user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]

        self.user32.SendInput.restype = wintypes.UINT
        self.user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), wintypes.INT]

        self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        self.user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, wintypes.WPARAM]

    def inject_text(self, text: str):
        """注入文本到当前光标位置"""
        if not text:
            return

        self._inject_via_clipboard(text)
        logger.info(f"文本已注入 ({len(text)} 字): {text[:30]}{'...' if len(text) > 30 else ''}")

    def _inject_via_clipboard(self, text: str):
        """剪贴板 + Ctrl+V"""
        original = self._get_clipboard_text()
        if not self._set_clipboard_text(text):
            return
        time.sleep(0.08)
        self._simulate_ctrl_v()
        time.sleep(0.15)
        if original is not None:
            self._set_clipboard_text(original)

    def _get_clipboard_text(self) -> str | None:
        """读取当前剪贴板文本（用于恢复）"""
        CF_UNICODETEXT = 13
        try:
            if not self.user32.OpenClipboard(0):
                return None
            h_data = self.user32.GetClipboardData(CF_UNICODETEXT)
            if not h_data:
                self.user32.CloseClipboard()
                return None
            p_data = self.kernel32.GlobalLock(h_data)
            if not p_data:
                self.user32.CloseClipboard()
                return None
            try:
                return ctypes.wstring_at(p_data)
            finally:
                self.kernel32.GlobalUnlock(h_data)
                self.user32.CloseClipboard()
        except Exception:
            return None

    def _set_clipboard_text(self, text: str) -> bool:
        """设置剪贴板文本，成功返回 True"""
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        for attempt in range(3):
            if self.user32.OpenClipboard(0):
                break
            time.sleep(0.01)
        else:
            logger.warning("无法打开剪贴板")
            return False

        try:
            self.user32.EmptyClipboard()
            text_data = text.encode('utf-16-le') + b'\x00\x00'
            h_mem = self.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_data))
            if not h_mem:
                logger.warning(f"GlobalAlloc 失败 (size={len(text_data)})")
                return False
            p_mem = self.kernel32.GlobalLock(h_mem)
            if not p_mem:
                logger.warning("GlobalLock 失败")
                return False
            ctypes.memmove(p_mem, text_data, len(text_data))
            self.kernel32.GlobalUnlock(h_mem)
            self.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            return True
        finally:
            self.user32.CloseClipboard()

    def _simulate_ctrl_v(self):
        """模拟 Ctrl+V — SendInput，失败时回退到 keybd_event"""
        inputs = (_INPUT * 4)()

        # Ctrl down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = VK_CONTROL
        inputs[0].ki.wScan = SC_CTRL

        # V down
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wVk = VK_V
        inputs[1].ki.wScan = SC_V

        # V up
        inputs[2].type = INPUT_KEYBOARD
        inputs[2].ki.wVk = VK_V
        inputs[2].ki.wScan = SC_V
        inputs[2].ki.dwFlags = KEYEVENTF_KEYUP

        # Ctrl up
        inputs[3].type = INPUT_KEYBOARD
        inputs[3].ki.wVk = VK_CONTROL
        inputs[3].ki.wScan = SC_CTRL
        inputs[3].ki.dwFlags = KEYEVENTF_KEYUP

        sent = self.user32.SendInput(4, inputs, ctypes.sizeof(_INPUT))
        if sent == 4:
            time.sleep(0.05)
            return

        # SendInput 被 UIPI 阻止，回退到 keybd_event
        # keybd_event 会设置系统键盘状态，GetKeyState 能看到 Ctrl 按下，而 PostMessage 做不到
        logger.warning(f"SendInput 被阻止 ({sent}/4)，使用 keybd_event 回退")
        self.user32.keybd_event(VK_CONTROL, SC_CTRL, 0, 0)
        time.sleep(0.03)
        self.user32.keybd_event(VK_V, SC_V, 0, 0)
        time.sleep(0.03)
        self.user32.keybd_event(VK_V, SC_V, KEYEVENTF_KEYUP, 0)
        time.sleep(0.03)
        self.user32.keybd_event(VK_CONTROL, SC_CTRL, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
