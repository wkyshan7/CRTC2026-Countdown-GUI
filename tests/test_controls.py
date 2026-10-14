import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from crtc.ui.control import Control
from crtc.ui.display import SCORE_RECTS
from crtc.runtime import PROJECT_ROOT
from crtc.teams import parse_teams
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest


class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=PROJECT_ROOT)
        self.control = Control(config_path=Path(self.directory.name) / 'config.json')

    def tearDown(self):
        self.control.ticker.stop()
        self.control.display.scroll_timer.stop()
        self.control.display.hide()
        self.control.hide()
        self.control.display.deleteLater()
        self.control.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def click_score(self, key, button):
        display = self.control.display
        scale = min(display.width() / 1920, display.height() / 1080)
        center = SCORE_RECTS[key].center()
        point = QPoint(round(center.x() * scale + (display.width() - 1920 * scale) / 2),
                       round(center.y() * scale + (display.height() - 1080 * scale) / 2))
        QTest.mouseClick(display, button, pos=point)

    def test_score_clicks_with_letterboxing_and_config_independence(self):
        c = self.control
        c.display.resize(800, 600)
        c.display.show()
        self.app.processEvents()
        c.fields['title'].setText('尚未应用的标题')
        c.score_fields['left_score'].setValue(3)
        self.assertEqual(c.data['left_score'], 3)
        self.assertNotEqual(self.control.config_store.load()['title'], '尚未应用的标题')
        self.click_score('left_score', Qt.MouseButton.LeftButton)
        self.assertEqual(c.data['left_score'], 0)
        self.click_score('left_score', Qt.MouseButton.RightButton)
        self.assertEqual(c.data['left_score'], 0)
        self.click_score('right_score', Qt.MouseButton.LeftButton)
        self.assertEqual(c.score_fields['right_score'].value(), 1)
        self.click_score('right_score', Qt.MouseButton.RightButton)
        self.assertEqual(c.data['right_score'], 0)
        c.score_fields['right_score'].setValue(2)
        c.apply_config()
        self.assertEqual(self.control.config_store.load()['right_score'], 2)

    def test_import_and_persist_display_settings(self):
        c = self.control
        filename = Path(self.directory.name) / 'teams.txt'
        filename.write_bytes('甲队\r\n乙队\n甲队\n\n'.encode('utf-8-sig'))
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(filename), '')):
            c.import_teams()
        self.assertEqual(c.fields['left_team'].count(), 2)
        c.fields['left_team'].setCurrentText('乙队')
        c.fields['english'].setPlainText('ROUND\nONE')
        c.fields['team_font_size'].setValue(60)
        c.fields['messages'].setPlainText('第一条\n\n第二条')
        c.apply_config()
        saved = self.control.config_store.load()
        self.assertEqual(saved['teams'], ['甲队', '乙队'])
        self.assertEqual(saved['left_team'], '乙队')
        self.assertEqual(saved['english'], 'ROUND\nONE')
        self.assertEqual(saved['team_font_size'], 60)
        self.assertEqual(c.display.messages(), ['第一条', '第二条'])
        c.display.message_offset = -10000
        c.display.advance_scroll()
        self.assertEqual(c.display.message_index, 1)
        c.display.message_offset = -10000
        c.display.advance_scroll()
        self.assertEqual(c.display.message_index, 0)

    def test_txt_encodings_and_invalid_import(self):
        self.assertEqual(parse_teams('红队\n蓝队'.encode('gbk')), ['红队', '蓝队'])
        with self.assertRaises(ValueError):
            parse_teams(b'\n  \r\n')
        with self.assertRaises(ValueError):
            parse_teams(('队' * 81).encode())

    def test_control_forwards_phase_and_timer_events_to_music(self):
        c = self.control
        backend = Mock()
        c.music.backend = backend
        c.start_timer()
        backend.play.assert_called_once()
        c.technical_pause()
        backend.set_phase.assert_called_with('technical')
        self.assertEqual(backend.play.call_count, 2)
        c.toggle_timer()
        backend.pause.assert_called_once()
        c.set_phase('competition')
        backend.set_phase.assert_called_with('competition')
        c.start_timer()
        self.assertEqual(backend.play.call_count, 3)
        backend.stop.reset_mock()
        c.timer.clock = lambda: c.timer.deadline + 1
        c.tick()
        backend.stop.assert_called_once()

    def test_technical_auto_start_option_is_saved_and_respected(self):
        c = self.control
        c.fields['technical_auto_start'].setChecked(False)
        c.apply_config()
        self.assertFalse(c.config_store.load()['technical_auto_start'])
        c.toggle_timer()
        c.technical_pause()
        self.assertEqual(c.timer.seconds(), 120)
        self.assertFalse(c.timer.running)
        c.fields['technical_auto_start'].setChecked(True)
        c.apply_config()
        self.assertTrue(c.config_store.load()['technical_auto_start'])
        c.technical_pause()
        self.assertTrue(c.timer.running)

    def test_space_binding_starts_and_resumes_without_toggling_pause(self):
        c = self.control
        self.assertEqual(c.start_shortcut.context(), Qt.ShortcutContext.ApplicationShortcut)
        self.assertFalse(c.start_shortcut.autoRepeat())
        c.set_phase('competition')
        c.start_shortcut.activated.emit()
        self.assertTrue(c.timer.running)
        deadline = c.timer.deadline
        c.start_shortcut.activated.emit()
        self.assertEqual(c.timer.deadline, deadline)
        c.toggle_timer()
        self.assertFalse(c.timer.running)
        c.start_shortcut.activated.emit()
        self.assertTrue(c.timer.running)

    def test_fullscreen_exit_restores_manageable_window(self):
        d = self.control.display
        d.resize(800, 450)
        d.show()
        self.app.processEvents()
        self.control.show_on_screen()
        self.app.processEvents()
        self.assertTrue(d.isFullScreen())
        d.toggle_fullscreen()
        self.app.processEvents()
        self.assertFalse(d.isFullScreen())
        self.assertLessEqual(d.width(), 800)
        self.assertLessEqual(d.height(), 450)
        self.assertTrue(d.screen().availableGeometry().contains(d.geometry()))
        d.enter_fullscreen()
        self.app.processEvents()
        d.exit_fullscreen()
        self.app.processEvents()
        self.assertFalse(d.isFullScreen())

    def test_dark_palette_readability_and_existing_timer_controls(self):
        dark = QPalette()
        dark.setColor(QPalette.ColorRole.WindowText, QColor('white'))
        dark.setColor(QPalette.ColorRole.Window, QColor('#222222'))
        previous = self.app.palette()
        try:
            self.app.setPalette(dark)
            self.control.show()
            self.app.processEvents()
            self.assertEqual(self.control.palette().color(QPalette.ColorRole.WindowText).name(), '#252525')
            self.assertEqual(self.control.score_fields['left_score'].palette().color(QPalette.ColorRole.Base).name(), '#ffffff')
            c = self.control
            c.toggle_timer()
            c.technical_pause()
            self.assertEqual(c.timer.seconds(), 120)
            self.assertTrue(c.timer.running)
            c.toggle_timer()
            c.set_phase('competition')
            self.assertEqual(c.timer.seconds(), 240)
            self.assertFalse(c.tech_button.isEnabled())
        finally:
            self.app.setPalette(previous)


if __name__ == '__main__':
    unittest.main()
