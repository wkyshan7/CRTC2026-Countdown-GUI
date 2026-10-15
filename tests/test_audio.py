"""以模拟播放器验证淡入淡出时序，避免依赖扬声器和真实等待。"""

import unittest
from unittest.mock import Mock

from crtc.ui.audio import QtMusicBackend, FADE_DURATION_MS, MUSIC_VOLUME
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication


class AudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.player = Mock()
        self.player.source.return_value = QUrl()
        self.player.setSource.side_effect = lambda url: setattr(
            self.player.source, 'return_value', url
        )
        self.output = Mock()
        self.output.volume.return_value = 0.0
        self.music = QtMusicBackend(player=self.player, output=self.output)

    def tearDown(self):
        self.music.fade.stop()
        self.music.deleteLater()

    def test_shared_track_does_not_seek_stop_or_reload(self):
        self.music.set_phase('preparation')
        self.music.play()
        self.music.set_phase('technical')
        self.player.setSource.assert_called_once()
        self.player.stop.assert_not_called()
        self.player.setPosition.assert_not_called()

    def test_play_fades_from_silence_to_target_volume(self):
        self.music.set_phase('preparation')
        self.music.play()
        self.music.fade.setCurrentTime(FADE_DURATION_MS // 2)
        volume = self.output.setVolume.call_args.args[0]
        self.assertGreater(volume, 0)
        self.assertLess(volume, MUSIC_VOLUME)
        self.music.fade.setCurrentTime(FADE_DURATION_MS)
        self.output.setVolume.assert_called_with(MUSIC_VOLUME)

    def test_pause_and_stop_wait_for_fade_and_resume_cancels_pending_pause(self):
        self.music.set_phase('preparation')
        self.output.volume.return_value = 0.6
        self.music.pause()
        self.player.pause.assert_not_called()
        self.music.fade.setCurrentTime(FADE_DURATION_MS)
        self.player.pause.assert_called_once()
        self.music.pause()
        self.music.play()
        self.music.fade.setCurrentTime(FADE_DURATION_MS)
        self.assertEqual(self.player.pause.call_count, 1)
        self.music.stop()
        self.player.stop.assert_not_called()
        self.music.fade.setCurrentTime(FADE_DURATION_MS)
        self.player.stop.assert_called_once()

    def test_competition_fades_out_and_shutdown_finishes_after_fade(self):
        self.music.set_phase('preparation')
        self.output.volume.return_value = 0.6
        self.music.set_phase('competition')
        self.music.play()
        self.player.play.assert_not_called()
        self.music.fade.setCurrentTime(FADE_DURATION_MS)
        self.player.stop.assert_called_once()
        callback = Mock()
        self.music.shutdown(callback)
        callback.assert_not_called()
        self.music.fade.setCurrentTime(FADE_DURATION_MS)
        callback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
