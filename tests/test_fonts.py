# SPDX-License-Identifier: GPL-3.0-or-later
"""验证项目字体加载和中英文混排时的实际字体选择。"""

import unittest

from crtc.ui.fonts import load_fonts, text_font
from PySide6.QtGui import QTextLayout
from PySide6.QtWidgets import QApplication


class FontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()

    def families_used(self, text, font):
        layout = QTextLayout(text, font)
        layout.beginLayout()
        layout.createLine().setLineWidth(1000)
        layout.endLayout()
        return {run.rawFont().familyName() for run in layout.glyphRuns()}

    def test_all_supplied_fonts_load(self):
        fonts = load_fonts()
        self.assertEqual(len(fonts), 15)
        self.assertIn('Geometos', fonts['Geometos.ttf'])
        self.assertIn('OPPOSans', fonts['OPPOSans-R-2.ttf'])
        self.assertIn('Outfit', fonts['Outfit-Regular.otf'])

    def test_chinese_and_regular_latin_use_requested_families(self):
        families = self.families_used('比赛 Outfit 02:00', text_font(32))
        self.assertEqual(families, {'OPPOSans', 'Outfit'})

    def test_emphasized_uppercase_uses_geometos(self):
        self.assertEqual(
            self.families_used('CRTC FINAL MATCH', text_font(32, emphasis=True)), {'Geometos'}
        )


if __name__ == '__main__':
    unittest.main()
