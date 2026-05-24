"""
全局快捷键监听模块 - 基于 keyboard 库的键盘钩子
"""
import logging
from typing import Callable, Optional

import keyboard

logger = logging.getLogger('guyuInput')

VALID_MODIFIERS = {'ctrl', 'alt', 'shift', 'win'}


class HotkeyManager:
    """全局快捷键管理器 - 支持按住录音 / 松开停止"""

    def __init__(self, hotkey_str: str = "ctrl+alt+v"):
        self.hotkey_str = hotkey_str
        self._is_pressed = False
        self._on_press: Optional[Callable] = None
        self._on_release: Optional[Callable] = None
        self._hook_id = None

    def register_callbacks(self, on_press: Callable, on_release: Callable):
        """注册按下 / 松开回调"""
        self._on_press = on_press
        self._on_release = on_release
        self._register_hook()
        logger.info(f"快捷键已注册: {self.hotkey_str}")

    def set_hotkey(self, hotkey_str: str) -> bool:
        """更换快捷键"""
        if not self.validate_hotkey(hotkey_str):
            return False

        self.hotkey_str = hotkey_str
        if self._hook_id is not None:
            keyboard.unhook(self._hook_id)
        self._register_hook()
        logger.info(f"快捷键已更换为: {hotkey_str}")
        return True

    def unregister(self):
        """注销快捷键"""
        if self._hook_id is not None:
            keyboard.unhook(self._hook_id)
            self._hook_id = None
        self._is_pressed = False

    def _register_hook(self):
        """注册键盘钩子"""
        parts = set(self.hotkey_str.lower().split('+'))

        def hook_event(e):
            if e.event_type not in ('down', 'up'):
                return

            mods = set()
            if 'ctrl' in parts and (keyboard.is_pressed('ctrl') or keyboard.is_pressed('right ctrl')):
                mods.add('ctrl')
            if 'alt' in parts and (keyboard.is_pressed('alt') or keyboard.is_pressed('right alt')):
                mods.add('alt')
            if 'shift' in parts and (keyboard.is_pressed('shift') or keyboard.is_pressed('right shift')):
                mods.add('shift')
            if 'win' in parts and (keyboard.is_pressed('windows') or keyboard.is_pressed('right windows')):
                mods.add('win')

            required_mods = parts & VALID_MODIFIERS
            if mods != required_mods:
                if self._is_pressed and e.event_type == 'up':
                    # 修饰键松开了，视为按键释放
                    self._is_pressed = False
                    if self._on_release:
                        self._on_release()
                return

            main_keys = parts - VALID_MODIFIERS
            for mk in main_keys:
                if e.name.lower() == mk:
                    if e.event_type == 'down' and not self._is_pressed:
                        self._is_pressed = True
                        if self._on_press:
                            self._on_press()
                    elif e.event_type == 'up' and self._is_pressed:
                        self._is_pressed = False
                        if self._on_release:
                            self._on_release()
                    break

        self._hook_id = keyboard.hook(hook_event)

    @staticmethod
    def validate_hotkey(hotkey_str: str) -> bool:
        """验证快捷键格式"""
        parts = hotkey_str.lower().split('+')
        if len(parts) < 2:
            return False
        mods = [p for p in parts if p in VALID_MODIFIERS]
        if len(mods) == 0 or len(mods) == len(parts):
            return False
        return True
