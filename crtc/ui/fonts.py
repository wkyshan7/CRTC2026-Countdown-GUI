# SPDX-License-Identifier: GPL-3.0-or-later
"""随应用加载字体，统一处理中英文字体及强调样式。"""

from functools import lru_cache

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from crtc.runtime import PROJECT_ROOT

FONT_DIRECTORY = PROJECT_ROOT / 'assets' / 'font'


@lru_cache(maxsize=1)
def load_fonts():
    """注册项目字体，不要求用户在操作系统中安装字体。"""
    if QApplication.instance() is None:
        raise RuntimeError('加载字体前必须创建 QApplication。')

    registered = {}
    for path in sorted(FONT_DIRECTORY.iterdir()):
        if path.suffix.lower() in ('.ttf', '.otf'):
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                raise RuntimeError(f'无法加载字体：{path.name}')
            registered[path.name] = QFontDatabase.applicationFontFamilies(font_id)
    return registered


def text_font(pixel_size=None, bold=False, emphasis=False):
    """英文用 Outfit，强调大写用 Geometos，中文回退到 OPPOSans。"""
    font = QFont()
    font.setFamilies(['Geometos' if emphasis else 'Outfit', 'OPPOSans'])
    if pixel_size is not None:
        font.setPixelSize(pixel_size)
    # Geometos 仅提供 Regular，其字形本身即用于强调。
    font.setWeight(QFont.Weight.Bold if bold and not emphasis else QFont.Weight.Normal)
    return font


def apply_application_fonts():
    """设置控件默认字体；正文英文优先 Outfit，中文回退至 OPPOSans。"""
    load_fonts()
    font = text_font()
    font.setPointSize(9)
    QApplication.instance().setFont(font)
