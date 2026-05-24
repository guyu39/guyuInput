"""
文本注入模块 - 通过 Win32 SendInput 将文字输出到当前光标位置
"""
import ctypes
import time
import logging
from ctypes import wintypes

logger = logging.getLogger('guyuInput')


class TextInjector:
    """文本注入器 - 短文本逐字符 SendInput，长文本剪贴板粘贴"""

    INPUT_KEYBOARD = 1
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    VK_CONTROL = 0x11
    VK_V = 0x56
    KEYEVENTF_KEYDOWN = 0x0000

    # 超过此长度使用剪贴板方式
    CLIPBOARD_THRESHOLD = 50

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def inject_text(self, text: str):
        """注入文本到当前光标位置"""
        if not text:
            return

        if len(text) <= self.CLIPBOARD_THRESHOLD:
            self._inject_by_char(text)
        else:
            self._inject_by_clipboard(text)

        logger.info(f"文本已注入 ({len(text)} 字): {text[:30]}{'...' if len(text) > 30 else ''}")

    def _inject_by_char(self, text: str):
        """逐字符 SendInput"""
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("ki", KEYBDINPUT),
            ]

        for ch in text:
            char_code = ord(ch)
            inputs = (INPUT * 2)()

            inputs[0].type = self.INPUT_KEYBOARD
            inputs[0].ki.wScan = char_code
            inputs[0].ki.dwFlags = self.KEYEVENTF_UNICODE

            inputs[1].type = self.INPUT_KEYBOARD
            inputs[1].ki.wScan = char_code
            inputs[1].ki.dwFlags = self.KEYEVENTF_UNICODE | self.KEYEVENTF_KEYUP

            self.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
            time.sleep(0.005)

    def _inject_by_clipboard(self, text: str):
        """剪贴板 + Ctrl+V"""
        self._set_clipboard_text(text)
        time.sleep(0.05)
        self._simulate_ctrl_v()

    def _set_clipboard_text(self, text: str):
        """设置剪贴板文本"""
        CF_UNICODETEXT = 13

        self.user32.OpenClipboard(0)
        self.user32.EmptyClipboard()

        text_data = text.encode('utf-16-le') + b'\x00\x00'
        GMEM_MOVEABLE = 0x0002
        GMEM_ZEROINIT = 0x0040
        h_mem = self.kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(text_data))
        p_mem = self.kernel32.GlobalLock(h_mem)
        ctypes.memmove(p_mem, text_data, len(text_data))
        self.kernel32.GlobalUnlock(h_mem)

        self.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        self.user32.CloseClipboard()

    def _simulate_ctrl_v(self):
        """模拟 Ctrl+V"""
        self.user32.keybd_event(self.VK_CONTROL, 0, self.KEYEVENTF_KEYDOWN, 0)
        time.sleep(0.01)
        self.user32.keybd_event(self.VK_V, 0, self.KEYEVENTF_KEYDOWN, 0)
        time.sleep(0.01)
        self.user32.keybd_event(self.VK_V, 0, self.KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
        self.user32.keybd_event(self.VK_CONTROL, 0, self.KEYEVENTF_KEYUP, 0)
