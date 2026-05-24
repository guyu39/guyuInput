"""
设置面板 - ASR 配置 / 快捷键 / 音频设备（单页垂直排列）
"""
import ctypes
import json
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QLineEdit, QComboBox, QScrollArea, QFrame, QApplication
)

DARK_BG = "#0f172a"
GLASS_BG = "rgba(15, 23, 42, 0.95)"
CARD_BG = "#1e293b"
BORDER = "rgba(255,255,255,0.05)"

BTN_BG = "#2563eb"
BTN_HOVER = "#3b82f6"


class _NoWheelCombo(QComboBox):
    """禁用滚轮切换的下拉框"""

    def wheelEvent(self, event):
        event.ignore()


class SettingsPage(QWidget):
    """设置面板 — 单页滚动"""

    closed = Signal()
    config_changed = Signal(str, str)
    credentials_save = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(480, 580)

        self._asr_mode = "auto"
        self._provider = "xunfei"
        self._credentials = {}
        self._recording_hotkey = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 标题栏 ──
        header = QWidget()
        header.setStyleSheet(
            f"background: {DARK_BG}; border-bottom: 1px solid {BORDER};"
            f"border-top-left-radius: 16px; border-top-right-radius: 16px;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        title = QLabel("设置")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #94a3b8; border: none;
                border-radius: 8px; font-size: 16px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)
        close_btn.clicked.connect(self.closed.emit)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)

        # ── 滚动区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {DARK_BG}; border: none; }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: #334155; border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #475569; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0; border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(
            f"background: {DARK_BG};"
            f"border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;"
        )
        content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        cv = QVBoxLayout(content)
        cv.setContentsMargins(20, 20, 28, 20)
        cv.setSpacing(20)

        # ── 语音识别 ──
        self._build_asr_section(cv)
        cv.addWidget(_divider())

        # ── 快捷键 ──
        self._build_hotkey_section(cv)
        cv.addWidget(_divider())

        # ── 音频设备 ──
        self._build_audio_section(cv)
        cv.addWidget(_divider())

        # ── 文本后处理 ──
        self._build_postprocess_section(cv)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        self.setStyleSheet(f"""
            SettingsPage {{
                background: {GLASS_BG};
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 16px;
            }}
        """)

    # ================================================================
    # ASR 区块
    # ================================================================

    def _build_asr_section(self, parent_layout):
        parent_layout.addWidget(_section_label("语音识别"))

        # 识别模式 → 下拉菜单
        parent_layout.addWidget(_sub_label("识别模式"))
        self._mode_combo = _NoWheelCombo()
        self._mode_combo.setStyleSheet(_combo_style())
        self._mode_combo.addItems(["自动切换", "仅在线", "仅离线"])
        self._mode_combo.currentIndexChanged.connect(
            lambda i: self._on_mode_change(["auto", "online", "offline"][i])
        )
        parent_layout.addWidget(self._mode_combo)

        # 供应商 → 下拉菜单
        parent_layout.addWidget(_sub_label("API 供应商"))
        self._prov_combo = _NoWheelCombo()
        self._prov_combo.setStyleSheet(_combo_style())
        self._prov_combo.addItems(["讯飞", "豆包", "阿里", "MiniMax"])
        self._prov_combo.currentIndexChanged.connect(
            lambda i: self._on_provider_change(["xunfei", "doubao", "ali", "minimax"][i])
        )
        parent_layout.addWidget(self._prov_combo)

        # 凭证字段
        self._cred_widget = QWidget()
        self._cred_widget.setStyleSheet("background: transparent;")
        self._cred_layout = QVBoxLayout(self._cred_widget)
        self._cred_layout.setContentsMargins(0, 0, 0, 0)
        self._cred_layout.setSpacing(8)
        self._cred_fields: dict[str, QLineEdit] = {}
        self._cred_labels: list[QLabel] = []
        self._rebuild_cred_fields("xunfei")
        parent_layout.addWidget(self._cred_widget)

        # 保存按钮
        save_btn = QPushButton("保存凭证")
        save_btn.setStyleSheet(_primary_btn_style())
        save_btn.clicked.connect(self._save_credentials)
        parent_layout.addWidget(save_btn)

    def _rebuild_cred_fields(self, provider: str):
        for lbl in self._cred_labels:
            self._cred_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._cred_labels.clear()
        for f in self._cred_fields.values():
            self._cred_layout.removeWidget(f)
            f.deleteLater()
        self._cred_fields.clear()

        fields = {
            "xunfei": ["xunfei_app_id", "xunfei_api_key", "xunfei_api_secret"],
            "doubao": ["doubao_app_id", "doubao_access_token"],
            "ali": ["ali_access_key_id", "ali_access_key_secret", "ali_app_key"],
            "minimax": ["minimax_api_key", "minimax_group_id"],
        }

        labels = {
            "app_id": "App ID", "api_key": "API Key", "api_secret": "API Secret",
            "access_token": "Access Token", "access_key_id": "AccessKey ID",
            "access_key_secret": "AccessKey Secret", "app_key": "App Key",
            "group_id": "Group ID",
        }

        for full_key in fields.get(provider, []):
            short = full_key.replace(f"{provider}_", "")
            lbl = QLabel(labels.get(short, short))
            lbl.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
            self._cred_labels.append(lbl)
            self._cred_layout.addWidget(lbl)

            edit = QLineEdit()
            edit.setPlaceholderText(f"输入 {labels.get(short, short)}")
            if "secret" in short or "key" in short or "token" in short:
                edit.setEchoMode(QLineEdit.Password)
            edit.setStyleSheet(_input_style())
            edit.setText(self._credentials.get(full_key, ""))
            self._cred_fields[full_key] = edit
            self._cred_layout.addWidget(edit)

    def _on_mode_change(self, mode: str):
        self._asr_mode = mode
        self.config_changed.emit("asr_mode", mode)

    def _on_provider_change(self, provider: str):
        self._provider = provider
        self._rebuild_cred_fields(provider)

    def _save_credentials(self):
        creds = {}
        prefix = f"{self._provider}_"
        for full_key, edit in self._cred_fields.items():
            creds[full_key.replace(prefix, "")] = edit.text()
            self._credentials[full_key] = edit.text()
        self.credentials_save.emit(self._provider, json.dumps(creds, ensure_ascii=False))

        # 移除旧的已保存提示
        if hasattr(self, '_status_label') and self._status_label:
            self._cred_layout.removeWidget(self._status_label)
            self._status_label.deleteLater()
        self._status_label = QLabel("已保存")
        self._status_label.setStyleSheet("color: #4ade80; font-size: 12px; background: transparent;")
        self._cred_layout.addWidget(self._status_label)

    # ================================================================
    # 快捷键区块
    # ================================================================

    def _build_hotkey_section(self, parent_layout):
        parent_layout.addWidget(_section_label("快捷键"))

        parent_layout.addWidget(_sub_label("录音快捷键"))

        self._hotkey_display = QLineEdit()
        self._hotkey_display.setReadOnly(True)
        self._hotkey_display.setAlignment(Qt.AlignCenter)
        self._hotkey_display.setStyleSheet(_input_style() + "font-size: 16px; font-weight: bold;")
        self._hotkey_display.setText("ctrl+alt+v")
        parent_layout.addWidget(self._hotkey_display)

        self._hotkey_record_btn = QPushButton("录制新快捷键")
        self._hotkey_record_btn.setStyleSheet(_primary_btn_style())
        self._hotkey_record_btn.clicked.connect(self._toggle_hotkey_record)
        parent_layout.addWidget(self._hotkey_record_btn)

        hint = QLabel("快捷键需要至少一个修饰键 (Ctrl/Alt/Shift/Win) + 一个普通键")
        hint.setStyleSheet("color: #64748b; font-size: 12px; background: transparent;")
        hint.setWordWrap(True)
        parent_layout.addWidget(hint)

    def _toggle_hotkey_record(self):
        self._recording_hotkey = not self._recording_hotkey
        if self._recording_hotkey:
            self._hotkey_record_btn.setText("按下组合键...")
            self._hotkey_record_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #dc2626; color: white; font-size: 13px; font-weight: bold;
                    border: none; border-radius: 8px; padding: 10px 24px;
                }}
                QPushButton:hover {{ background: #ef4444; }}
            """)
            self._hotkey_display.setText("")
            # 禁用输入法，确保字母按键不被拼音拦截
            self._saved_ime = None
            try:
                hwnd = int(self.window().winId())
                self._saved_ime = ctypes.windll.imm32.ImmAssociateContext(hwnd, 0)
            except Exception:
                pass
            self.window().activateWindow()
            self.grabKeyboard()
            QApplication.instance().installEventFilter(self)
        else:
            self._hotkey_record_btn.setText("录制新快捷键")
            self._hotkey_record_btn.setStyleSheet(_primary_btn_style())
            QApplication.instance().removeEventFilter(self)
            self.releaseKeyboard()
            # 恢复输入法
            if self._saved_ime is not None:
                try:
                    hwnd = int(self.window().winId())
                    ctypes.windll.imm32.ImmAssociateContext(hwnd, self._saved_ime)
                except Exception:
                    pass
                self._saved_ime = None

    def eventFilter(self, obj, event):
        if self._recording_hotkey and event.type() == QEvent.KeyPress:
            self._handle_key(event)
            return True
        return super().eventFilter(obj, event)

    def _handle_key(self, event):
        mods = []
        if event.modifiers() & Qt.ControlModifier:
            mods.append("ctrl")
        if event.modifiers() & Qt.AltModifier:
            mods.append("alt")
        if event.modifiers() & Qt.ShiftModifier:
            mods.append("shift")
        if event.modifiers() & Qt.MetaModifier:
            mods.append("win")

        key = event.key()
        # 修饰键本身忽略
        if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
            return

        # 直接用 key code 映射，不依赖 event.text()（IME 下可能为空）
        key_name = None
        if Qt.Key_A <= key <= Qt.Key_Z:
            key_name = chr(key).lower()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            key_name = chr(key)
        else:
            key_name = {
                Qt.Key_Space: "space", Qt.Key_Tab: "tab", Qt.Key_Backspace: "backspace",
                Qt.Key_Return: "enter", Qt.Key_Enter: "enter", Qt.Key_Escape: "esc",
                Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4",
                Qt.Key_F5: "f5", Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8",
                Qt.Key_F9: "f9", Qt.Key_F10: "f10", Qt.Key_F11: "f11", Qt.Key_F12: "f12",
                Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
                Qt.Key_Comma: ",", Qt.Key_Period: ".", Qt.Key_Slash: "/",
                Qt.Key_Semicolon: ";", Qt.Key_QuoteDbl: "'", Qt.Key_BracketLeft: "[",
                Qt.Key_BracketRight: "]", Qt.Key_Backslash: "\\", Qt.Key_Minus: "-",
                Qt.Key_Equal: "=", Qt.Key_QuoteLeft: "`",
            }.get(key)

        if key_name and mods:
            hotkey = "+".join(mods + [key_name])
            self._hotkey_display.setText(hotkey)
            self.config_changed.emit("record_hotkey", hotkey)
            self._toggle_hotkey_record()

    # ================================================================
    # 音频设备区块
    # ================================================================

    def _build_audio_section(self, parent_layout):
        parent_layout.addWidget(_section_label("音频设备"))

        parent_layout.addWidget(_sub_label("麦克风设备"))
        self._device_combo = _NoWheelCombo()
        self._device_combo.setStyleSheet(_combo_style())
        self._device_combo.addItem("默认设备", -1)
        parent_layout.addWidget(self._device_combo)

        refresh_btn = QPushButton("刷新设备列表")
        refresh_btn.setStyleSheet(_secondary_btn_style())
        refresh_btn.clicked.connect(lambda: self.config_changed.emit("refresh_devices", ""))
        parent_layout.addWidget(refresh_btn)

    def set_device(self, device_id: int):
        self._device_combo.setCurrentIndex(
            next((i for i in range(self._device_combo.count())
                  if self._device_combo.itemData(i) == device_id), 0)
        )

    def load_devices(self, devices_json: str):
        self._device_combo.clear()
        self._device_combo.addItem("默认设备", -1)
        try:
            devices = json.loads(devices_json or "[]")
            seen = set()
            for d in devices:
                did = d["id"]
                if did in seen:
                    continue
                seen.add(did)
                name = d["name"]
                if d.get("is_default"):
                    name += " (默认)"
                self._device_combo.addItem(name, did)
        except (json.JSONDecodeError, KeyError):
            pass

    # ================================================================
    # 文本后处理区块
    # ================================================================

    def _build_postprocess_section(self, parent_layout):
        parent_layout.addWidget(_section_label("文本后处理"))

        # 词典校正开关
        parent_layout.addWidget(_sub_label("词典校正"))
        self._dict_toggle = _NoWheelCombo()
        self._dict_toggle.setStyleSheet(_combo_style())
        self._dict_toggle.addItems(["开启", "关闭"])
        self._dict_toggle.currentIndexChanged.connect(
            lambda i: self.config_changed.emit("dictionary_enabled", "true" if i == 0 else "false")
        )
        parent_layout.addWidget(self._dict_toggle)

        # AI 润色开关
        parent_layout.addWidget(_sub_label("AI 润色"))
        self._polish_toggle = _NoWheelCombo()
        self._polish_toggle.setStyleSheet(_combo_style())
        self._polish_toggle.addItems(["关闭", "开启"])
        self._polish_toggle.currentIndexChanged.connect(
            lambda i: self.config_changed.emit("polish_enabled", "true" if i == 1 else "false")
        )
        parent_layout.addWidget(self._polish_toggle)

        # 润色供应商
        parent_layout.addWidget(_sub_label("润色供应商"))
        self._polish_prov_combo = _NoWheelCombo()
        self._polish_prov_combo.setStyleSheet(_combo_style())
        self._polish_prov_combo.addItems(["OpenAI", "豆包", "DeepSeek", "自定义"])
        self._polish_prov_combo.currentIndexChanged.connect(
            lambda i: self._on_polish_provider_change(["openai", "doubao", "deepseek", "custom"][i])
        )
        parent_layout.addWidget(self._polish_prov_combo)

        # API Key
        parent_layout.addWidget(_sub_label("API Key"))
        self._polish_key_edit = QLineEdit()
        self._polish_key_edit.setEchoMode(QLineEdit.Password)
        self._polish_key_edit.setPlaceholderText("输入 API Key")
        self._polish_key_edit.setStyleSheet(_input_style())
        self._polish_key_edit.editingFinished.connect(self._save_polish_key)
        parent_layout.addWidget(self._polish_key_edit)

        # 模型
        parent_layout.addWidget(_sub_label("模型"))
        self._polish_model_combo = _NoWheelCombo()
        self._polish_model_combo.setStyleSheet(_combo_style())
        self._polish_model_combo.setEditable(True)
        self._polish_model_combo.addItems([
            "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo",
            "doubao-pro-32k", "doubao-lite-32k",
            "deepseek-chat",
        ])
        self._polish_model_combo.currentTextChanged.connect(
            lambda t: self.config_changed.emit("polish_model", t)
        )
        parent_layout.addWidget(self._polish_model_combo)

        # 自定义 URL
        parent_layout.addWidget(_sub_label("自定义 URL（可选）"))
        self._polish_url_edit = QLineEdit()
        self._polish_url_edit.setPlaceholderText("https://api.openai.com/v1")
        self._polish_url_edit.setStyleSheet(_input_style())
        self._polish_url_edit.editingFinished.connect(self._save_polish_url)
        parent_layout.addWidget(self._polish_url_edit)

        # 润色强度
        parent_layout.addWidget(_sub_label("润色强度"))
        self._polish_mode_combo = _NoWheelCombo()
        self._polish_mode_combo.setStyleSheet(_combo_style())
        self._polish_mode_combo.addItems(["仅标点", "适度润色（推荐）", "深度润色"])
        self._polish_mode_combo.currentIndexChanged.connect(
            lambda i: self.config_changed.emit("polish_mode", ["light", "moderate", "deep"][i])
        )
        parent_layout.addWidget(self._polish_mode_combo)

    def _on_polish_provider_change(self, provider: str):
        self.config_changed.emit("polish_provider", provider)
        # 切换供应商时更新默认模型
        default_models = {"openai": "gpt-4o-mini", "doubao": "doubao-pro-32k",
                          "deepseek": "deepseek-chat", "custom": ""}
        if provider in default_models:
            self._polish_model_combo.setCurrentText(default_models[provider])

    def _save_polish_key(self):
        self.config_changed.emit("polish_api_key", self._polish_key_edit.text())

    def _save_polish_url(self):
        self.config_changed.emit("polish_base_url", self._polish_url_edit.text())

    def load_config(self, config_json: str):
        try:
            cfg = json.loads(config_json or "{}")
            # 恢复识别模式
            mode = cfg.get("asr_mode", "auto")
            self._asr_mode = mode
            mode_index = {"auto": 0, "online": 1, "offline": 2}.get(mode, 0)
            self._mode_combo.setCurrentIndex(mode_index)
            # 恢复快捷键
            hotkey = cfg.get("record_hotkey", "ctrl+alt+v")
            self._hotkey_display.setText(hotkey)
            # 恢复凭证
            for k, v in cfg.items():
                if any(k.startswith(p) for p in ["xunfei_", "doubao_", "ali_", "minimax_"]):
                    self._credentials[k] = v
            # 恢复供应商
            provider = cfg.get("asr_provider", "")
            if not provider:
                # 兼容旧数据：从凭证键推断
                for p in ["xunfei", "doubao", "ali", "minimax"]:
                    if any(k.startswith(f"{p}_") for k in self._credentials):
                        provider = p
                        break
            if provider:
                self._provider = provider
                prov_index = {"xunfei": 0, "doubao": 1, "ali": 2, "minimax": 3}.get(provider, 0)
                self._prov_combo.setCurrentIndex(prov_index)
                self._rebuild_cred_fields(provider)

            # 恢复后处理配置
            dict_enabled = cfg.get("dictionary_enabled", "true")
            self._dict_toggle.setCurrentIndex(0 if dict_enabled == "true" else 1)
            polish_enabled = cfg.get("polish_enabled", "false")
            self._polish_toggle.setCurrentIndex(1 if polish_enabled == "true" else 0)
            polish_prov = cfg.get("polish_provider", "openai")
            prov_index = {"openai": 0, "doubao": 1, "deepseek": 2, "custom": 3}.get(polish_prov, 0)
            self._polish_prov_combo.setCurrentIndex(prov_index)
            self._polish_key_edit.setText(cfg.get("polish_api_key", ""))
            model = cfg.get("polish_model", "gpt-4o-mini")
            self._polish_model_combo.setCurrentText(model)
            self._polish_url_edit.setText(cfg.get("polish_base_url", ""))
            polish_mode = cfg.get("polish_mode", "moderate")
            mode_index = {"light": 0, "moderate": 1, "deep": 2}.get(polish_mode, 1)
            self._polish_mode_combo.setCurrentIndex(mode_index)
        except (json.JSONDecodeError, KeyError):
            pass


# ================================================================
# 样式辅助
# ================================================================

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("border: none; border-top: 1px solid rgba(255,255,255,0.06);")
    return line


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #e2e8f0; font-size: 15px; font-weight: 600; background: transparent;")
    return lbl


def _sub_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
    return lbl


def _input_style() -> str:
    return f"""
        QLineEdit {{
            background: {CARD_BG}; color: white; border: 1px solid #334155;
            border-radius: 8px; padding: 10px 12px; font-size: 13px;
        }}
        QLineEdit:focus {{ border-color: #60a5fa; }}
    """


def _primary_btn_style() -> str:
    return f"""
        QPushButton {{
            background: {BTN_BG}; color: white; font-size: 13px; font-weight: bold;
            border: none; border-radius: 8px; padding: 10px 24px;
        }}
        QPushButton:hover {{ background: {BTN_HOVER}; }}
    """


def _secondary_btn_style() -> str:
    return f"""
        QPushButton {{
            background: {CARD_BG}; color: #94a3b8; font-size: 13px;
            border: 1px solid #334155; border-radius: 8px; padding: 10px 24px;
        }}
        QPushButton:hover {{ background: #334155; }}
    """


def _combo_style() -> str:
    return f"""
        QComboBox {{
            background: {CARD_BG}; color: white; border: 1px solid #334155;
            border-radius: 8px; padding: 10px 12px; font-size: 13px;
        }}
        QComboBox:focus {{ border-color: #60a5fa; }}
        QComboBox::drop-down {{ border: none; }}
        QComboBox QAbstractItemView {{
            background: {CARD_BG}; color: white; border: 1px solid #334155;
            selection-background-color: {BTN_BG};
        }}
    """
