"""构建控制窗口的双栏布局与输入控件；业务回调由窗口提供。"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QLabel, QGroupBox, QComboBox, QPlainTextEdit, QApplication, QCheckBox)


def build_control_layout(window):
    root = QWidget()
    window.setCentralWidget(root)
    layout = QVBoxLayout(root)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    window.status = QLabel()
    window.status.setStyleSheet('font-size: 22px; font-weight: bold; padding: 12px; background: #fff5bf;')
    layout.addWidget(window.status)
    columns = QHBoxLayout()
    columns.setSpacing(16)
    settings = QVBoxLayout()
    operations = QVBoxLayout()
    columns.addLayout(settings, 3)
    columns.addLayout(operations, 2)
    layout.addLayout(columns, 1)
    score_group = QGroupBox('即时比分（无需保存配置）')
    score_form = QFormLayout(score_group)
    window.score_fields = {}
    for key, title in [('left_score', '红方大比分'), ('right_score', '蓝方大比分')]:
        field = QSpinBox()
        field.setRange(0, 3)
        field.setValue(window.data[key])
        field.valueChanged.connect(lambda value, score_key=key: window.set_score(score_key, value))
        window.score_fields[key] = field
        score_form.addRow(title, field)
    score_tip = QLabel('大屏比分：左键 +1，右键 -1；超出 0～3 归零。')
    score_tip.setWordWrap(True)
    score_form.addRow(score_tip)
    operations.addWidget(score_group)
    group = QGroupBox('比赛信息与显示配置')
    form = QFormLayout(group)
    form.setVerticalSpacing(6)
    window.fields = {}
    labels = dict(title='赛事名称', match='赛事轮次', left_team='红方队伍', right_team='蓝方队伍',
                  left_score='红方大比分', right_score='蓝方大比分', preparation='准备时长（秒）',
                  technical='技术暂停时长（秒）', competition='比赛时长（秒）',
                  english='左上角英文（可换行）', team_font_size='队名字号（像素）', messages='滚动信息（每行一条）')
    for key, value in window.data.items():
        if key in ('left_score', 'right_score', 'teams', 'technical_auto_start'):
            continue
        if key in ('left_team', 'right_team'):
            field = QComboBox()
            field.setEditable(True)
            field.lineEdit().setMaxLength(80)
            field.addItems(list(dict.fromkeys([value] + window.data['teams'])))
            field.setCurrentText(value)
        elif key in ('english', 'messages'):
            field = QPlainTextEdit(value)
            field.setFixedHeight(48 if key == 'english' else 70)
            field.setPlaceholderText('每行一条，按顺序循环滚动' if key == 'messages' else 'FINAL\nMATCH')
        elif isinstance(value, str):
            field = QLineEdit(value)
            field.setMaxLength(80)
        else:
            field = QSpinBox()
            field.setRange(18 if key == 'team_font_size' else 1,
                           90 if key == 'team_font_size' else 5999)
            field.setValue(value)
        window.fields[key] = field
        form.addRow(labels[key], field)
    settings.addWidget(group)
    config_buttons = QHBoxLayout()
    window.button(config_buttons, 'TXT 导入队伍', window.import_teams)
    window.button(config_buttons, '保存并应用配置', window.apply_config)
    settings.addLayout(config_buttons)
    settings.addWidget(QLabel('时长修改在下次重置或切换阶段时生效。'))
    settings.addStretch()
    timer_group = QGroupBox('计时控制')
    timer_layout = QVBoxLayout(timer_group)
    auto_start = QCheckBox('技术暂停后立即开始')
    auto_start.setChecked(window.data['technical_auto_start'])
    window.fields['technical_auto_start'] = auto_start
    timer_layout.addWidget(auto_start)
    row = QHBoxLayout()
    window.button(row, '准备阶段 / 重置', lambda: window.set_phase('preparation'))
    window.button(row, '正式比赛 / 重置', lambda: window.set_phase('competition'))
    timer_layout.addLayout(row)
    row = QHBoxLayout()
    window.start_button = window.button(row, '开始', window.toggle_timer)
    window.tech_button = window.button(row, '技术暂停（覆盖计时）', window.technical_pause)
    timer_layout.addLayout(row)
    pause_tip = QLabel('技术暂停仅适用于准备阶段。选项修改后请保存配置。')
    pause_tip.setWordWrap(True)
    timer_layout.addWidget(pause_tip)
    operations.addWidget(timer_group)
    screen_group = QGroupBox('大屏展示')
    screen_layout = QVBoxLayout(screen_group)
    window.screens = QComboBox()
    for i, screen in enumerate(QApplication.screens()):
        window.screens.addItem(f'{i + 1} · {screen.name()} · {screen.size().width()}×{screen.size().height()}')
    window.screens.setMinimumContentsLength(16)
    window.screens.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    screen_layout.addWidget(window.screens)
    window.button(screen_layout, '在所选屏幕全屏展示', window.show_on_screen)
    shortcuts = QLabel('大屏快捷键：F11 全屏 / Esc 退出全屏\nF2 打开操作面板 / 空格 开始或继续')
    shortcuts.setWordWrap(True)
    screen_layout.addWidget(shortcuts)
    operations.addWidget(screen_group)
    operations.addStretch()
