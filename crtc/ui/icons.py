# SPDX-License-Identifier: GPL-3.0-or-later
"""应用窗口与 Windows 任务栏图标。"""

import sys

from PySide6.QtGui import QIcon

from crtc.runtime import PROJECT_ROOT

APP_ICON_PATH = PROJECT_ROOT / 'assets' / 'images' / 'app-icon.ico'


def apply_application_icon(app):
    """同时供源码和 EXE 使用，两个顶层窗口继承应用默认图标。"""
    if sys.platform == 'win32':
        import ctypes

        # 独立的应用标识使源码运行时也不会被任务栏归为 Python 图标。
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CRTCCompetition.Countdown')

    icon = QIcon(str(APP_ICON_PATH))
    if icon.isNull():
        raise RuntimeError(f'无法加载应用图标：{APP_ICON_PATH}')
    app.setWindowIcon(icon)
