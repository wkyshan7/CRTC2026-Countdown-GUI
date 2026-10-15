"""控制窗口浅色主题，独立于操作系统的深色模式。"""

from PySide6.QtGui import QColor, QPalette


def apply_control_theme(window):
    """同时设置调色板和控件样式，避免系统深色主题覆盖文字与输入框。"""
    palette = QPalette()
    colors = {
        'Window': '#fafafa',
        'WindowText': '#252525',
        'Base': '#ffffff',
        'AlternateBase': '#f0f0f0',
        'Text': '#252525',
        'Button': '#eeeeee',
        'ButtonText': '#252525',
        'Highlight': '#ffd400',
        'HighlightedText': '#252525',
        'ToolTipBase': '#ffffff',
        'ToolTipText': '#252525',
        'PlaceholderText': '#777777',
    }
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    window.setPalette(palette)

    window.setStyleSheet(
        'QWidget { font-family: "Outfit", "OPPOSans"; color: #252525; background-color: #fafafa; } '
        'QPushButton { padding: 6px; background: #eeeeee; border: 1px solid #cccccc; border-radius: 4px; } '
        'QPushButton:hover { background: #fff1a6; } QWidget:disabled { color: #777777; } '
        'QGroupBox { font-weight: bold; } '
        'QLineEdit, QSpinBox, QComboBox, QPlainTextEdit { '
        'padding: 3px; background: white; color: #252525; '
        'selection-background-color: #ffd400; selection-color: #252525; } '
        'QComboBox QAbstractItemView { background: white; color: #252525; }'
    )
