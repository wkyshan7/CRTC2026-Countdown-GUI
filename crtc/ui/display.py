# SPDX-License-Identifier: GPL-3.0-or-later
"""大屏绘制、滚动消息、快捷键和比分点击。"""

import time

from PySide6.QtCore import Qt, QRect, QRectF, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPixmap, QShortcut, QKeySequence, QFontMetricsF
from PySide6.QtWidgets import QWidget

from .fonts import text_font
from .header import draw_match_header
from crtc.runtime import PROJECT_ROOT

SCORE_RECTS = {'left_score': QRectF(810, 650, 120, 85), 'right_score': QRectF(990, 650, 120, 85)}
TICKER_HEIGHT = 64
TICKER_FONT_SIZE = 36


def ticker_font():
    """绘制和宽度测量使用相同的加粗字幕字体。"""
    return text_font(TICKER_FONT_SIZE, bold=True)


class Display(QWidget):
    """在 1920×1080 设计坐标中绘制主体，按窗口比例缩放。"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        # 资源只在窗口创建时加载，避免每帧绘制重复读取磁盘。
        self.logo = QPixmap(str(PROJECT_ROOT / 'assets' / 'images' / 'CRTCLogo.png'))
        if self.logo.isNull():
            raise RuntimeError('无法加载 assets/images/CRTCLogo.png')
        self.header_decoration = QPixmap(
            str(PROJECT_ROOT / 'assets' / 'images' / 'header-emblem-yellow.png')
        )
        if self.header_decoration.isNull():
            raise RuntimeError('无法加载 assets/images/header-emblem-yellow.png')

        self.reset_scroll()
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.advance_scroll)
        self.scroll_timer.start(16)
        self.setWindowTitle('CRTC 比赛大屏 · F11 全屏 · F2 操作面板')
        self.resize(1280, 720)
        self.windowed_geometry = QRect(self.geometry())

        for key, callback in [
            ('F11', self.toggle_fullscreen),
            ('Escape', self.exit_fullscreen),
            ('F2', controller.show_panel),
        ]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)

    def toggle_fullscreen(self):
        self.exit_fullscreen() if self.isFullScreen() else self.enter_fullscreen()

    def enter_fullscreen(self, screen=None):
        """记录普通窗口大小，再进入指定屏幕，避免保存为整屏尺寸。"""
        if not self.isFullScreen():
            self.windowed_geometry = QRect(
                self.normalGeometry() if self.isMaximized() else self.geometry()
            )
        if screen is not None:
            if self.windowHandle() is None:
                self.show()
            self.windowHandle().setScreen(screen)
            # 定位到目标屏幕，但不把普通窗口放大到整屏。
            self.move(screen.availableGeometry().topLeft())
        self.showFullScreen()

    def exit_fullscreen(self):
        if not self.isFullScreen():
            return
        available = self.screen().availableGeometry()
        saved = self.windowed_geometry
        width = min(saved.width(), 1280, int(available.width() * 0.8))
        height = min(saved.height(), 720, int(available.height() * 0.8))
        # 为标题栏和边框留空间，保证退出后可以直接拖动。
        x = max(available.left() + 16, min(saved.x(), available.right() - width - 16))
        y = max(available.top() + 40, min(saved.y(), available.bottom() - height - 40))
        self.showNormal()
        self.setGeometry(QRect(x, y, width, height))

    def reset_scroll(self):
        self.message_index = 0
        self.message_offset = self.ticker_rect().width()
        self.last_scroll_time = time.monotonic()

    def ticker_rect(self):
        """在设计坐标中定位消息条，使其始终贴合实际窗口底边和左右边。"""
        scale = min(self.width() / 1920, self.height() / 1080)
        offset_x = (self.width() - 1920 * scale) / 2
        offset_y = (self.height() - 1080 * scale) / 2
        return QRectF(
            -offset_x / scale,
            (self.height() - offset_y) / scale - TICKER_HEIGHT,
            self.width() / scale,
            TICKER_HEIGHT,
        )

    def resizeEvent(self, event):
        self.reset_scroll()
        super().resizeEvent(event)

    def messages(self):
        return [
            line.strip() for line in self.controller.data['messages'].splitlines() if line.strip()
        ]

    def advance_scroll(self):
        """按真实经过时间移动字幕，测量完整文本离开后再切下一条。"""
        now = time.monotonic()
        elapsed = now - self.last_scroll_time
        self.last_scroll_time = now

        messages = self.messages()
        if messages:
            self.message_offset -= elapsed * 140
            font = ticker_font()
            width = QFontMetricsF(font).horizontalAdvance(
                messages[self.message_index % len(messages)]
            )
            if self.message_offset < -width:
                self.message_index = (self.message_index + 1) % len(messages)
                self.message_offset = self.ticker_rect().width()
            self.update()

    def mousePressEvent(self, event):
        """把鼠标坐标反向映射到设计坐标，缩放后也能准确点击比分。"""
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            scale = min(self.width() / 1920, self.height() / 1080)
            point = QPointF(
                (event.position().x() - (self.width() - 1920 * scale) / 2) / scale,
                (event.position().y() - (self.height() - 1080 * scale) / 2) / scale,
            )
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
        # 主体按 16:9 等比缩放；ticker_rect 单独延伸到实际窗口底边。
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor('white'))

        scale = min(self.width() / 1920, self.height() / 1080)
        p.translate((self.width() - 1920 * scale) / 2, (self.height() - 1080 * scale) / 2)
        p.scale(scale, scale)
        yellow, dark = QColor('#ffd400'), QColor('#303030')

        def label(
            rect,
            text,
            size,
            color=dark,
            bold=False,
            align=Qt.AlignmentFlag.AlignCenter,
            emphasis=False,
        ):
            font = text_font(size, bold=bold, emphasis=emphasis)
            p.setFont(font)
            p.setPen(color)
            # Fit long team names and titles without overlapping adjacent content.
            lines = text.splitlines() or ['']
            while (
                max(p.fontMetrics().horizontalAdvance(line) for line in lines) > rect.width() - 12
                or p.fontMetrics().height() * len(lines) > rect.height()
            ) and font.pixelSize() > 14:
                font.setPixelSize(font.pixelSize() - 1)
                p.setFont(font)
            p.drawText(rect, align, text)

        d = self.controller.data

        # 顶部赛事标题与品牌标识。
        draw_match_header(p, d, self.header_decoration)
        logo_area = QRectF(1495, 48, 380, 120)
        ratio = min(logo_area.width() / self.logo.width(), logo_area.height() / self.logo.height())
        logo_rect = QRectF(0, 0, self.logo.width() * ratio, self.logo.height() * ratio)
        logo_rect.moveCenter(logo_area.center())
        p.drawPixmap(logo_rect, self.logo, QRectF(self.logo.rect()))

        # 中部双方队名、比赛时间和可点击比分。
        for x, key in [(310, 'left_team'), (1270, 'right_team')]:
            label(QRectF(x, 465, 340, 115), d[key], d['team_font_size'], bold=True)
        seconds = self.controller.timer.seconds()
        label(
            QRectF(675, 460, 570, 175),
            f'{seconds // 60:02d}:{seconds % 60:02d}',
            148,
            QColor('#dc1515') if seconds <= 10 else dark,
            True,
        )
        label(SCORE_RECTS['left_score'], str(d['left_score']), 66, QColor('#df0000'), True)
        label(QRectF(935, 650, 50, 85), ':', 58, dark, True)
        label(SCORE_RECTS['right_score'], str(d['right_score']), 66, QColor('#003bbb'), True)

        status = (
            '时间到'
            if seconds == 0
            else ('进行中' if self.controller.timer.running else '等待开始')
        )
        label(
            QRectF(610, 375, 700, 60),
            f'{self.controller.phase_name} · {status}',
            26,
            QColor('#777777'),
        )

        # 底部条始终铺满窗口，裁剪区域保证滚动文字不会溢出。
        messages = self.messages()
        ticker = self.ticker_rect()
        p.fillRect(ticker, yellow)
        if messages:
            p.save()
            p.setClipRect(ticker)
            font = ticker_font()
            p.setFont(font)
            p.setPen(dark)
            metrics = QFontMetricsF(font)
            baseline = ticker.center().y() + (metrics.ascent() - metrics.descent()) / 2
            p.drawText(
                QPointF(ticker.left() + self.message_offset, baseline),
                messages[self.message_index % len(messages)],
            )
            p.restore()

        p.end()
