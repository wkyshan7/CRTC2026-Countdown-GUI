# SPDX-License-Identifier: GPL-3.0-or-later
"""配置和比赛操作的协调：保存、计时、比分及屏幕选择。"""

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLineEdit,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QCheckBox,
)

from crtc.config import ConfigStore, bounded_score
from crtc.countdown import Countdown
from crtc.teams import parse_teams
from crtc.music import PhaseMusic
from .display import Display
from .control_layout import build_control_layout
from .theme import apply_control_theme
from .fonts import apply_application_fonts


class Control(QMainWindow):
    """协调两个窗口及业务状态，计时和音乐实现分别交给独立模块。"""

    def __init__(self, config_path=None, music_backend=None):
        super().__init__()
        apply_application_fonts()

        # 先恢复持久化配置，再创建依赖配置值的计时器和界面控件。
        self.config_store = ConfigStore() if config_path is None else ConfigStore(config_path)
        self.data = self.config_store.load()

        # 技术暂停属于准备阶段，但使用独立的显示名称与音乐阶段标识。
        self.phase = 'preparation'
        self.music_phase = 'preparation'
        self.music = PhaseMusic(music_backend)
        self.music.set_enabled(self.data['music_enabled'])
        self.music.set_volume(self.data['music_volume'])
        self.phase_name = '准备阶段'
        self.timer = Countdown(self.data[self.phase])

        # pending 只在首次开始时消费；in_precountdown 用于识别 5 秒倒数结束事件。
        self.precountdown_pending = False
        self.in_precountdown = False
        self.technical_music_hold = False

        self.display = Display(self)
        self.setWindowTitle('CRTC 配置与比赛控制')
        self.resize(940, 640)
        build_control_layout(self)
        apply_control_theme(self)

        # 应用级快捷键覆盖两个窗口，禁用自动重复避免长按多次触发。
        self.start_shortcut = QShortcut(QKeySequence('Space'), self)
        self.start_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.start_shortcut.setAutoRepeat(False)
        self.start_shortcut.activated.connect(self.start_timer)

        # 定时器只负责刷新；实际剩余时间由单调时钟计算。
        self.ticker = QTimer(self)
        self.ticker.timeout.connect(self.tick)
        self.ticker.start(100)
        self.tick()

    def button(self, layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def apply_config(self):
        """校验并保存草稿配置，成功后同步显示与即时控制范围。"""
        data = self.data.copy()
        for key, field in self.fields.items():
            if isinstance(field, QCheckBox):
                data[key] = field.isChecked()
            elif isinstance(field, QComboBox):
                data[key] = field.currentText().strip()
            elif isinstance(field, QPlainTextEdit):
                data[key] = field.toPlainText().strip()[: 10000 if key == 'messages' else 80]
            else:
                data[key] = field.text().strip() if isinstance(field, QLineEdit) else field.value()

        if any(not data[key] for key in ('title', 'match', 'left_team', 'right_team')):
            QMessageBox.warning(self, '配置未保存', '赛事名称、轮次和双方队伍不能为空。')
            return
        for key in ('left_score', 'right_score'):
            data[key] = bounded_score(data[key], data['score_limit'])
        if not self.save_data(data):
            return

        # 保存成功后才生效，避免磁盘写入失败时界面与配置不一致。
        reset_scroll = data['messages'] != self.data['messages']
        self.data = data
        self.music.set_enabled(self.data['music_enabled'])
        self.music.set_volume(self.data['music_volume'])

        # 程序同步数值时屏蔽信号，避免递归触发比分保存。
        for key, field in self.score_fields.items():
            field.blockSignals(True)
            field.setRange(0, self.data['score_limit'])
            field.setValue(self.data[key])
            field.blockSignals(False)

        if reset_scroll:
            self.display.reset_scroll()
        self.tick()

    def save_data(self, data):
        """把存储异常转换为面向操作员的提示。"""
        try:
            self.config_store.save(data)
        except OSError as exc:
            QMessageBox.warning(self, '保存失败', str(exc))
            return False
        return True

    def set_music_enabled(self, enabled):
        """开关即时生效并单独保存，不应用其他尚未保存的表单内容。"""
        self._save_music_option('music_enabled', enabled)

    def set_music_volume(self, percent):
        """音量即时保存，播放器负责平滑过渡到新的目标音量。"""
        self._save_music_option('music_volume', percent)

    def _save_music_option(self, key, value):
        data = self.data.copy()
        data[key] = value
        if not self.save_data(data):
            field = self.fields[key]
            field.blockSignals(True)
            if key == 'music_enabled':
                field.setChecked(self.data[key])
            else:
                field.setValue(self.data[key])
            field.blockSignals(False)
            return
        self.data = data
        self.music.set_enabled(self.data['music_enabled'])
        self.music.set_volume(self.data['music_volume'])
        self.tick()

    def set_score(self, key, value):
        """即时更新并持久化比分，不读取尚未应用的比赛信息草稿。"""
        self.data[key] = bounded_score(value, self.data['score_limit'])
        field = self.score_fields[key]
        field.blockSignals(True)
        field.setValue(self.data[key])
        field.blockSignals(False)
        self.display.update()
        self.save_data(self.data)

    def import_teams(self):
        """导入候选名单，同时保留双方当前选项与未保存的输入。"""
        filename, _ = QFileDialog.getOpenFileName(self, '导入队伍', '', '队伍文件 (*.txt)')
        if not filename:
            return

        try:
            names = parse_teams(Path(filename).read_bytes())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, '导入失败', str(exc))
            return

        data = self.data.copy()
        data['teams'] = names
        if not self.save_data(data):
            return
        self.data = data

        for key in ('left_team', 'right_team'):
            field = self.fields[key]
            selected = field.currentText()
            field.clear()
            field.addItems(names)
            field.setCurrentText(selected)
        self.statusBar().showMessage(f'已导入 {len(names)} 支队伍，请下拉选择并保存配置。', 8000)

    def set_phase(self, phase):
        """重置到指定阶段的等待状态，并清除上一阶段的临时标记。"""
        if self.timer.running:
            answer = QMessageBox.question(self, '重置计时', '计时正在进行，确定切换并重置倒计时？')
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.phase = phase
        self.precountdown_pending = phase == 'competition'
        self.in_precountdown = False
        self.technical_music_hold = False
        self.music_phase = phase
        self.music.reset()
        self.phase_name = '准备阶段' if phase == 'preparation' else '正式比赛'
        self.timer.reset(self.data[phase])
        self.tick()

    def technical_pause(self):
        """覆盖准备计时，是否立即计时由配置决定，音乐保持连续。"""
        if self.phase != 'preparation':
            return

        self.phase_name = '技术暂停'
        self.music_phase = 'technical'

        # 即使取消技术暂停自动计时，已经播放的准备音乐也保持连续。
        self.technical_music_hold = self.music.state == 'playing'

        self.timer.reset(self.data['technical'])
        if self.data['technical_auto_start']:
            self.timer.start()
        self.tick()

    def toggle_timer(self):
        """手动操作接管计时，结束技术暂停等待时的音乐保持状态。"""
        self.technical_music_hold = False
        if self.timer.running:
            self.timer.pause()
        else:
            self._start_current_timer()
        self.tick()

    def start_timer(self):
        """空格开始或继续当前阶段；重复按下不会暂停正在运行的计时。"""
        self.technical_music_hold = False
        self._start_current_timer()
        self.tick()

    def _start_current_timer(self):
        """仅首次开始插入赛前倒数，暂停后的继续不会重复插入。"""
        if self.precountdown_pending:
            self.precountdown_pending = False
            if self.data['competition_precountdown']:
                self.in_precountdown = True
                self.phase_name = '比赛开始倒计时'
                self.timer.reset(5)

        self.timer.start()

    def tick(self):
        """先处理到期的阶段转换，再同步音乐状态和两个窗口的显示。"""
        if self.timer.finish_if_due():
            if self.in_precountdown:
                self.in_precountdown = False
                self.phase_name = '正式比赛'
                self.timer.reset(self.data['competition'])
                self.timer.start()
            else:
                QApplication.beep()

        seconds = self.timer.seconds()
        if seconds == 0:
            self.technical_music_hold = False

        self.score_tip.setText(
            f"大屏比分：左键 +1，右键 -1；超出 0～{self.data['score_limit']} 归零。"
        )
        music_running = (
            self.timer.running and not self.in_precountdown
        ) or self.technical_music_hold
        self.music.sync(self.music_phase, music_running, seconds)
        self.status.setText(f'{self.phase_name}  {seconds // 60:02d}:{seconds % 60:02d}')
        self.start_button.setText('暂停' if self.timer.running else '开始 / 继续')
        self.tech_button.setEnabled(self.phase == 'preparation')
        self.display.update()

    def show_panel(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def show_on_screen(self):
        screen = QApplication.screens()[self.screens.currentIndex()]
        self.display.enter_fullscreen(screen)

    def closeEvent(self, event):
        """有声后端先淡出再退出；第二次关闭请求放行，避免阻止 quit。"""
        shutdown = getattr(self.music.backend, 'shutdown', None)
        if callable(shutdown):
            if getattr(self, '_closing', False):
                event.accept()
                return

            event.ignore()
            self._closing = True
            self.ticker.stop()
            self.display.scroll_timer.stop()
            self.setEnabled(False)
            shutdown(QApplication.instance().quit)
            return

        self.music.stop()
        QApplication.instance().quit()
        event.accept()
