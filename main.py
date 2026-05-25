"""
guyuInput - Windows 智能语音输入法 (Qt 版本)
入口文件
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from backend import API, ConfigManager, init_logger, SystemTray
from ui import MainWindow


def _setup_high_dpi():
    """必须在 QApplication 创建前调用，确保 4K/高 DPI 显示器不虚化"""
    # Qt 6: AA_EnableHighDpiScaling / AA_DisableHighDpiScaling 已废弃（始终开启）
    # 关键：设置缩放因子舍入策略为 PassThrough，避免 Qt 对非整数缩放比取整导致发虚
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    # 适配 Windows 自定义缩放的字体渲染
    if hasattr(Qt, 'AA_Use96Dpi'):
        QApplication.setAttribute(Qt.AA_Use96Dpi, False)


def main():
    _setup_high_dpi()

    logger = init_logger()
    logger.info("=" * 50)
    logger.info("guyuInput (Qt) 启动中...")

    # Qt 应用
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，保留托盘

    # 配置
    config = ConfigManager()
    logger.info("配置管理器初始化完成")

    # 后端 API
    api = API(config)

    # 主窗口
    window = MainWindow()

    # ================================================================
    # 连线：API 信号 → 窗口更新
    # ================================================================

    api.recording_started.connect(lambda engine: window.show_recording(engine))
    api.recording_stopped.connect(lambda text, injected: window.show_idle())
    api.recording_error.connect(lambda msg: window.show_error(msg, auto_dismiss_ms=3000))
    api.volume_changed.connect(window.update_volume)
    api.silence_timeout.connect(lambda: window.show_error("未检测到语音，即将关闭", auto_dismiss_ms=2000))
    api.model_loading.connect(window.update_text)
    api.asr_partial.connect(window.update_text)
    api.asr_final.connect(window.update_text)
    api.asr_status.connect(window.recording.show_status)
    def _on_asr_error(msg: str):
        api.stop_recording(confirm=False)
        window.show_error(msg, auto_dismiss_ms=5000)
    api.asr_error.connect(_on_asr_error)
    api.config_loaded.connect(window.update_config_display)
    api.devices_loaded.connect(window.update_device_list)

    # 连线：窗口操作 → API 调用
    window.start_recording_signal.connect(api.start_recording)
    window.stop_recording_signal.connect(api.stop_recording)
    window.config_signal.connect(api.set_config)
    window.credentials_signal.connect(api.save_asr_credentials)
    window.refresh_devices_signal.connect(api.load_devices)

    # 首次运行检查
    first_run = config.get('first_run', 'true')
    if first_run == 'true':
        window.show_guide()
    else:
        window.show_idle()
        api.load_all_config()

    # 加载设备
    api.load_devices()

    # ================================================================
    # 系统托盘 — Qt 原生 QSystemTrayIcon，主线程运行，无需跨线程桥接
    # ================================================================

    def on_tray_show():
        logger.info("托盘：显示窗口")
        window.show()
        window.raise_()
        window.activateWindow()

    def on_tray_quit():
        logger.info("托盘：退出")
        QApplication.quit()

    tray = SystemTray()
    tray.setup(
        on_show=on_tray_show,
        on_settings=lambda: (window.show_settings(), on_tray_show()),
        on_quit=on_tray_quit,
    )

    # 退出前清理
    app.aboutToQuit.connect(api.shutdown)
    app.aboutToQuit.connect(tray.stop)

    # ================================================================
    # 启动
    # ================================================================

    window.show()
    logger.info("窗口已显示，启动 Qt 事件循环")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
