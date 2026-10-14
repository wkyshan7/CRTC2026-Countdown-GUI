"""应用创建与两个主窗口的启动。"""
import sys

from crtc.ui.control import Control
from PySide6.QtWidgets import QApplication


def run():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    control = Control()
    control.display.show()
    control.show()
    return app.exec()
