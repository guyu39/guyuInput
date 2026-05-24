import sqlite3
import os
import json
from typing import Any, Optional


class ConfigManager:
    """配置管理器 - SQLite 存储"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = os.path.join(os.path.expanduser("~"), ".guyuInput")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "config.db")

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_table()
        self._init_defaults()

    def _init_table(self):
        """初始化表结构"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def _init_defaults(self):
        """初始化默认配置"""
        defaults = {
            'first_run': 'true',
            'record_hotkey': 'ctrl+alt+v',
            'asr_mode': 'auto',
            'asr_provider': 'xunfei',
        }
        for key, value in defaults.items():
            if not self.get(key):
                self.set(key, value)

    def get(self, key: str, default: str = "") -> str:
        """获取字符串配置"""
        cur = self.conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

    def set(self, key: str, value: str):
        """设置字符串配置"""
        self.conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        return self.get(key, str(default)).lower() == 'true'

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default

    def get_json(self, key: str, default: Any = None) -> Any:
        """获取 JSON 配置"""
        val = self.get(key, "")
        if not val:
            return default
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default

    def set_json(self, key: str, value: Any):
        """设置 JSON 配置"""
        self.set(key, json.dumps(value, ensure_ascii=False))
