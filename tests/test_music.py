"""阶段背景音乐事件验证，无需音频设备。"""
import unittest
from unittest.mock import Mock, call

from crtc.music import PhaseMusic, MusicBackend


class MusicTests(unittest.TestCase):
    def setUp(self):
        self.backend = Mock(spec=MusicBackend)
        self.music = PhaseMusic(self.backend)

    def test_start_pause_resume_and_finish_emit_once(self):
        self.music.sync('preparation', False, 120)
        self.music.sync('preparation', True, 120)
        self.music.sync('preparation', True, 119)
        self.music.sync('preparation', False, 118)
        self.music.sync('preparation', True, 118)
        self.music.sync('preparation', False, 0)
        self.music.sync('preparation', False, 0)
        self.assertEqual(self.backend.mock_calls, [call.set_phase('preparation'), call.play(),
                         call.pause(), call.play(), call.stop()])

    def test_technical_preserves_preparation_playback_and_competition_stops_it(self):
        self.music.sync('preparation', True, 120)
        self.music.sync('technical', True, 120)
        self.music.sync('competition', False, 240)
        self.assertEqual(self.backend.mock_calls, [call.set_phase('preparation'), call.play(),
            call.set_phase('technical'),
            call.stop(), call.set_phase('competition')])

    def test_repeated_timeout_restarts_track(self):
        self.music.sync('technical', True, 100)
        self.music.reset()
        self.music.sync('technical', True, 120)
        self.assertEqual(self.backend.mock_calls, [call.set_phase('technical'), call.play(),
                         call.stop(), call.set_phase('technical'), call.play()])


if __name__ == '__main__':
    unittest.main()
