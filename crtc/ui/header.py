"""参考赛事视觉的左上角标题区，按文字宽度动态布局。"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QFontMetricsF

from .fonts import text_font


def fit_font(text, size, max_width, bold=False, emphasis=False, max_height=None):
    font = text_font(size, bold=bold, emphasis=emphasis)
    if bold and not emphasis:
        font.setWeight(QFont.Weight.Black)
    lines = text.splitlines() or ['']
    while font.pixelSize() > 12:
        metrics = QFontMetricsF(font)
        if (max(metrics.horizontalAdvance(line) for line in lines) <= max_width
                and (max_height is None or metrics.height() * len(lines) <= max_height)):
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def draw_match_header(painter, data, decoration):
    painter.save()
    yellow = QColor('#ffd400')
    dark = QColor('#292929')
    # 透明黄色环形图案置于文字背后，中心和图块间隙保持透明。
    area = QRectF(42, 48, 160, 160)
    ratio = min(area.width() / decoration.width(), area.height() / decoration.height())
    target = QRectF(0, 0, decoration.width() * ratio, decoration.height() * ratio)
    target.moveCenter(area.center())
    painter.drawPixmap(target, decoration, QRectF(decoration.rect()))

    title_font = fit_font(data['title'], 30, 1100)
    painter.setFont(title_font)
    painter.setPen(dark)
    painter.drawText(QRectF(94, 62, 1110, 48), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                     data['title'])

    english = data['english']
    letters = [char for char in english if char.isascii() and char.isalpha()]
    uppercase = bool(letters) and all(char.isupper() for char in letters)
    english_font = fit_font(english, 24, 280, bold=True, emphasis=uppercase, max_height=70)
    english_metrics = QFontMetricsF(english_font)
    english_width = max((english_metrics.horizontalAdvance(line) for line in english.splitlines()), default=0)
    match_font = fit_font(data['match'], 76, 1000 - english_width - 80, bold=True)
    match_width = QFontMetricsF(match_font).horizontalAdvance(data['match'])
    english_left = 100 + match_width + 24
    band = QRectF(100 + match_width - 12, 116, english_width + 96, 80)
    painter.fillRect(band, yellow)

    painter.setFont(match_font)
    painter.setPen(dark)
    painter.drawText(QRectF(100, 94, match_width + 12, 116),
                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, data['match'])
    painter.setFont(english_font)
    painter.setPen(QColor('white'))
    painter.drawText(QRectF(english_left, band.top(), english_width + 12, band.height()),
                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, english)
    painter.restore()
