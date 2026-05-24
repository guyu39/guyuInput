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


def main():
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
    api.asr_partial.connect(window.update_text)
    api.asr_final.connect(window.update_text)
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
    # 系统托盘
    # ================================================================

    tray = SystemTray()

    def on_tray_show():
        logger.info("托盘：显示窗口")
        window.show()
        window.raise_()
        window.activateWindow()

    def on_tray_quit():
        logger.info("托盘：退出")
        api.shutdown()
        tray.stop()
        QApplication.quit()

    tray.setup(on_tray_show, on_tray_quit)
    tray.run_in_thread()

    # ================================================================
    # 启动
    # ================================================================

    window.show()
    logger.info("窗口已显示，启动 Qt 事件循环")
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
