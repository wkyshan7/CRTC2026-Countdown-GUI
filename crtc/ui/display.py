"""大屏绘制、滚动消息、快捷键和比分点击。"""
import time

from PySide6.QtCore import Qt, QRectF, QTimer, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QShortcut, QKeySequence, QFontMetricsF
from PySide6.QtWidgets import QWidget

SCORE_RECTS = {'left_score': QRectF(810, 650, 120, 85),
               'right_score': QRectF(990, 650, 120, 85)}
TICKER_RECT = QRectF(80, 980, 1760, 64)


class Display(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.reset_scroll()
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.advance_scroll)
        self.scroll_timer.start(16)
        self.setWindowTitle('CRTC 比赛大屏 · F11 全屏 · F2 操作面板')
        self.resize(1280, 720)
        for key, callback in [('F11', self.toggle_fullscreen), ('Escape', self.showNormal),
                              ('F2', controller.show_panel)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def reset_scroll(self):
        self.message_index = 0
        self.message_offset = TICKER_RECT.width()
        self.last_scroll_time = time.monotonic()

    def messages(self):
        return [line.strip() for line in self.controller.data['messages'].splitlines() if line.strip()]

    def advance_scroll(self):
        now = time.monotonic()
        elapsed = now - self.last_scroll_time
        self.last_scroll_time = now
        messages = self.messages()
        if messages:
            self.message_offset -= elapsed * 140
            font = QFont('Microsoft YaHei')
            font.setPixelSize(26)
            width = QFontMetricsF(font).horizontalAdvance(messages[self.message_index % len(messages)])
            if self.message_offset < -width:
                self.message_index = (self.message_index + 1) % len(messages)
                self.message_offset = TICKER_RECT.width()
            self.update()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            scale = min(self.width() / 1920, self.height() / 1080)
            point = QPointF((event.position().x() - (self.width() - 1920 * scale) / 2) / scale,
                            (event.position().y() - (self.height() - 1080 * scale) / 2) / scale)
            for key, rect in SCORE_RECTS.items():
                if rect.contains(point):
                    delta = 1 if event.button() == Qt.MouseButton.LeftButton else -1
                    self.controller.set_score(key, self.controller.data[key] + delta)
                    return
        super().mousePressEvent(event)

    def closeEvent(self, event):
        self.controller.close()
        event.accept()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('white'))
        scale = min(self.width() / 1920, self.height() / 1080)
        p.translate((self.width() - 1920 * scale) / 2, (self.height() - 1080 * scale) / 2)
        p.scale(scale, scale)
        yellow, dark = QColor('#ffd400'), QColor('#303030')

        def label(rect, text, size, color=dark, bold=False, align=Qt.AlignmentFlag.AlignCenter):
            font = QFont('Microsoft YaHei', size)
            font.setPixelSize(size)
            font.setBold(bold)
            p.setFont(font)
            p.setPen(color)
            # Fit long team names and titles without overlapping adjacent content.
            lines = text.splitlines() or ['']
            while (max(p.fontMetrics().horizontalAdvance(line) for line in lines) > rect.width() - 12
                   or p.fontMetrics().height() * len(lines) > rect.height()) and font.pixelSize() > 14:
                font.setPixelSize(font.pixelSize() - 1)
                p.setFont(font)
            p.drawText(rect, align, text)

        d = self.controller.data
        label(QRectF(80, 55, 900, 45), d['title'], 30, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        p.fillRect(QRectF(80, 112, 290, 57), yellow)
        label(QRectF(84, 105, 150, 65), d['match'], 52, bold=True)
        label(QRectF(240, 114, 120, 51), d['english'], 21, bold=True)
        p.fillRect(QRectF(1500, 48, 56, 56), yellow)
        p.fillRect(QRectF(1556, 104, 56, 56), yellow)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(yellow)
        p.drawEllipse(QRectF(1532, 80, 48, 48))
        label(QRectF(1620, 55, 255, 100), 'CRTC', 86, bold=True)
        for x, key in [(310, 'left_team'), (1270, 'right_team')]:
            label(QRectF(x, 465, 340, 115), d[key], d['team_font_size'], bold=True)
        seconds = self.controller.timer.seconds()
        label(QRectF(675, 460, 570, 175), f'{seconds // 60:02d}:{seconds % 60:02d}',
              148, QColor('#dc1515') if seconds <= 10 else dark, True)
        label(SCORE_RECTS['left_score'], str(d['left_score']), 66, QColor('#df0000'), True)
        label(QRectF(935, 650, 50, 85), ':', 58, dark, True)
        label(SCORE_RECTS['right_score'], str(d['right_score']), 66, QColor('#003bbb'), True)
        status = '时间到' if seconds == 0 else ('进行中' if self.controller.timer.running else '等待开始')
        label(QRectF(610, 375, 700, 60), f'{self.controller.phase_name} · {status}', 26, QColor('#777777'))
        messages = self.messages()
        p.fillRect(TICKER_RECT, yellow)
        if messages:
            p.save()
            p.setClipRect(TICKER_RECT)
            font = QFont('Microsoft YaHei')
            font.setPixelSize(26)
            p.setFont(font)
            p.setPen(dark)
            metrics = QFontMetricsF(font)
            baseline = TICKER_RECT.center().y() + (metrics.ascent() - metrics.descent()) / 2
            p.drawText(QPointF(TICKER_RECT.left() + self.message_offset, baseline),
                       messages[self.message_index % len(messages)])
            p.restore()
        p.end()
