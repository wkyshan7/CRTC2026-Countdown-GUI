"""Monotonic countdown independent of the GUI."""
import math
import time


class Countdown:
    def __init__(self, seconds=120, clock=time.monotonic):
        self.clock = clock
        self.remaining = float(seconds)
        self.deadline = None

    @property
    def running(self):
        return self.deadline is not None

    def seconds(self):
        value = self.remaining if self.deadline is None else self.deadline - self.clock()
        return max(0, math.ceil(value))

    def start(self):
        if not self.running and self.remaining > 0:
            self.deadline = self.clock() + self.remaining

    def pause(self):
        if self.running:
            self.remaining = max(0, self.deadline - self.clock())
            self.deadline = None

    def reset(self, seconds):
        self.deadline = None
        self.remaining = float(seconds)

    def finish_if_due(self):
        if self.running and self.clock() >= self.deadline:
            self.reset(0)
            return True
        return False
