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
        self._required_mods: set[str] = set()
        self._main_keys: set[str] = set()
        self._parse_hotkey()

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
        self._parse_hotkey()
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

    def _parse_hotkey(self):
        parts = set(self.hotkey_str.lower().split('+'))
        self._required_mods = parts & VALID_MODIFIERS
        self._main_keys = parts - VALID_MODIFIERS

    def _register_hook(self):
        """注册键盘钩子 - suppress=False 确保不拦截系统快捷键"""
        self._hook_id = keyboard.hook(self._on_hook_event, suppress=False)

    def _on_hook_event(self, e):
        """钩子回调 - 必须快速返回，否则会影响系统键盘响应"""
        try:
            if e.event_type not in ('down', 'up'):
                return

            # 快速检查：修饰键数量不对就跳过
            mods = self._get_active_mods()
            if mods != self._required_mods:
                if self._is_pressed and e.event_type == 'up':
                    self._is_pressed = False
                    if self._on_release:
                        self._on_release()
                return

            # 检查是否匹配主键
            if e.name.lower() in self._main_keys:
                if e.event_type == 'down' and not self._is_pressed:
                    self._is_pressed = True
                    if self._on_press:
                        self._on_press()
                elif e.event_type == 'up' and self._is_pressed:
                    self._is_pressed = False
                    if self._on_release:
                        self._on_release()
        except Exception:
            logger.warning("键盘钩子回调异常", exc_info=True)

    def _get_active_mods(self) -> set[str]:
        """快速获取当前按下的修饰键集合"""
        mods = set()
        if self._required_mods:
            if 'ctrl' in self._required_mods and (keyboard.is_pressed('ctrl') or keyboard.is_pressed('right ctrl')):
                mods.add('ctrl')
            if 'alt' in self._required_mods and (keyboard.is_pressed('alt') or keyboard.is_pressed('right alt')):
                mods.add('alt')
            if 'shift' in self._required_mods and (keyboard.is_pressed('shift') or keyboard.is_pressed('right shift')):
                mods.add('shift')
            if 'win' in self._required_mods and (keyboard.is_pressed('windows') or keyboard.is_pressed('right windows')):
                mods.add('win')
        return mods

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
