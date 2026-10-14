import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont, QIcon
from core.config import AppConfig, ROOT
from apps.desktop_app.main_window import MainWindow

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--connect', action='store_true', help='启动后连接配置中的 UE')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('WISEYE Studio')
    app.setFont(QFont('Microsoft YaHei UI', 10))
    app.setWindowIcon(QIcon(str(ROOT/'LOGO.jpg')))
    (ROOT/'logs').mkdir(exist_ok=True)
    handler = RotatingFileHandler(ROOT/'logs/desktop_app.log', maxBytes=1000000, backupCount=3, encoding='utf8')
    logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    try:
        window = MainWindow(AppConfig.load())
    except (ValueError, OSError) as exc:
        QMessageBox.critical(None, 'WISEYE 配置错误', str(exc))
        return 1
    window.show()
    if args.connect:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, window.connect_ue)
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
