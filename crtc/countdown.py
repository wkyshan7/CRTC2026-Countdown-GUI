# SPDX-License-Identifier: GPL-3.0-or-later
"""独立于 GUI 的单调时钟倒计时，不受系统时间调整影响。"""

import math
import time


class Countdown:
    """运行时保存截止时间，暂停时保存精确剩余秒数，可注入时钟测试。"""

    def __init__(self, seconds=120, clock=time.monotonic):
        self.clock = clock
        self.remaining = float(seconds)
        self.deadline = None

    @property
    def running(self):
        return self.deadline is not None

    def seconds(self):
        """显示时向上取整，避免开始瞬间少显示一秒。"""
        value = self.remaining if self.deadline is None else self.deadline - self.clock()
        return max(0, math.ceil(value))

    def start(self):
        if not self.running and self.remaining > 0:
            self.deadline = self.clock() + self.remaining

    def pause(self):
        """暂停保留小数部分，多次暂停不会累积整秒误差。"""
        if self.running:
            self.remaining = max(0, self.deadline - self.clock())
            self.deadline = None

    def reset(self, seconds):
        self.deadline = None
        self.remaining = float(seconds)

    def finish_if_due(self):
        """到期仅返回一次 True，供调用方触发阶段转换或提示音。"""
        if self.running and self.clock() >= self.deadline:
            self.reset(0)
            return True
        return False
