import unittest
from crtc.countdown import Countdown


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.timer = Countdown(120, lambda: self.now)

    def test_pause_and_resume_preserve_fraction(self):
        self.timer.start()
        self.now += 3.25
        self.timer.pause()
        self.now += 50
        self.assertEqual(self.timer.seconds(), 117)
        self.timer.start()
        self.now += 116.75
        self.assertTrue(self.timer.finish_if_due())
        self.assertEqual(self.timer.seconds(), 0)
        self.assertFalse(self.timer.running)

    def test_override_stops_and_replaces_remaining(self):
        self.timer.start()
        self.now += 70
        self.timer.reset(120)
        self.assertEqual(self.timer.seconds(), 120)
        self.assertFalse(self.timer.running)

    def test_delayed_tick_never_goes_negative(self):
        self.timer.start()
        self.now += 200
        self.assertEqual(self.timer.seconds(), 0)
        self.assertTrue(self.timer.finish_if_due())
        self.assertFalse(self.timer.finish_if_due())


if __name__ == '__main__':
    unittest.main()
