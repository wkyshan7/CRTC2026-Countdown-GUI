"""应用创建与两个主窗口的启动。"""
import sys

from crtc.ui.control import Control
from crtc.ui.audio import QtMusicBackend
from PySide6.QtWidgets import QApplication


def run():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    music = QtMusicBackend(app)
    control = Control(music_backend=music)
    music.error.connect(lambda message: control.statusBar().showMessage(f'背景音乐播放失败：{message}', 15000))
    control.display.show()
    control.show()
    return app.exec()
