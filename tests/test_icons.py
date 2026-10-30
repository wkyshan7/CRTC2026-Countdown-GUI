# SPDX-License-Identifier: GPL-3.0-or-later
"""验证随程序分发的 ICO 可以作为应用图标加载。"""

import unittest

from crtc.ui.icons import apply_application_icon
from PySide6.QtWidgets import QApplication, QWidget


class IconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_application_icon_has_all_sizes_and_is_inherited_by_windows(self):
        previous = self.app.windowIcon()
        try:
            apply_application_icon(self.app)
            sizes = {size.width() for size in self.app.windowIcon().availableSizes()}
            self.assertEqual(sizes, {16, 24, 32, 48, 64, 128, 256})
            window = QWidget()
            self.assertFalse(window.windowIcon().isNull())
            self.assertFalse(window.windowIcon().pixmap(32, 32).isNull())
            window.deleteLater()
        finally:
            self.app.setWindowIcon(previous)


if __name__ == '__main__':
    unittest.main()
