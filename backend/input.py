"""
文本注入模块 - 通过 Win32 SendInput 将文字输出到当前光标位置
"""
import ctypes
import time
import logging
from ctypes import wintypes

logger = logging.getLogger('guyuInput')

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

VK_CONTROL = 0x11
VK_V = 0x56

# 超过此长度使用剪贴板方式
CLIPBOARD_THRESHOLD = 50


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", _KEYBDINPUT),
    ]


class TextInjector:
    """文本注入器 - 短文本逐字符 SendInput，长文本剪贴板粘贴"""

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def inject_text(self, text: str):
        """注入文本到当前光标位置"""
        if not text:
            return

        if len(text) <= CLIPBOARD_THRESHOLD:
            self._inject_by_char(text)
        else:
            self._inject_by_clipboard(text)

        logger.info(f"文本已注入 ({len(text)} 字): {text[:30]}{'...' if len(text) > 30 else ''}")

    def _inject_by_char(self, text: str):
        """逐字符 SendInput"""
        for ch in text:
            char_code = ord(ch)
            inputs = (_INPUT * 2)()

            inputs[0].type = INPUT_KEYBOARD
            inputs[0].ki.wScan = char_code
            inputs[0].ki.dwFlags = KEYEVENTF_UNICODE

            inputs[1].type = INPUT_KEYBOARD
            inputs[1].ki.wScan = char_code
            inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

            self.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(_INPUT))
            time.sleep(0.005)

    def _inject_by_clipboard(self, text: str):
        """剪贴板 + Ctrl+V（先保存再恢复原始剪贴板内容）"""
        original = self._get_clipboard_text()
        self._set_clipboard_text(text)
        time.sleep(0.05)
        self._simulate_ctrl_v()
        time.sleep(0.1)
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

    def _set_clipboard_text(self, text: str):
        """设置剪贴板文本"""
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        GMEM_ZEROINIT = 0x0040

        for attempt in range(3):
            if self.user32.OpenClipboard(0):
                break
            time.sleep(0.01)
        else:
            logger.warning("无法打开剪贴板")
            return

        try:
            self.user32.EmptyClipboard()

            text_data = text.encode('utf-16-le') + b'\x00\x00'
            h_mem = self.kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(text_data))
            p_mem = self.kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, text_data, len(text_data))
            self.kernel32.GlobalUnlock(h_mem)

            self.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        finally:
            self.user32.CloseClipboard()

    def _simulate_ctrl_v(self):
        """模拟 Ctrl+V - 使用 SendInput 原子发送，避免 keybd_event 卡键"""
        inputs = (_INPUT * 4)()

        # Ctrl down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = VK_CONTROL

        # V down
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wVk = VK_V

        # V up
        inputs[2].type = INPUT_KEYBOARD
        inputs[2].ki.wVk = VK_V
        inputs[2].ki.dwFlags = KEYEVENTF_KEYUP

        # Ctrl up
        inputs[3].type = INPUT_KEYBOARD
        inputs[3].ki.wVk = VK_CONTROL
        inputs[3].ki.dwFlags = KEYEVENTF_KEYUP

        self.user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(_INPUT))
        time.sleep(0.05)
