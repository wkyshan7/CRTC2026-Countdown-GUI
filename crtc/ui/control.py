"""配置和比赛操作的协调：保存、计时、比分及屏幕选择。"""
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QLineEdit, QPushButton,
    QComboBox, QPlainTextEdit, QFileDialog, QMessageBox, QCheckBox)

from crtc.config import ConfigStore, bounded_score
from crtc.countdown import Countdown
from crtc.teams import parse_teams
from crtc.music import PhaseMusic
from .display import Display
from .control_layout import build_control_layout
from .theme import apply_control_theme
from .fonts import apply_application_fonts

class Control(QMainWindow):
    def __init__(self, config_path=None, music_backend=None):
        super().__init__()
        apply_application_fonts()
        self.config_store = ConfigStore() if config_path is None else ConfigStore(config_path)
        self.data = self.config_store.load()
        self.phase = 'preparation'
        self.music_phase = 'preparation'
        self.music = PhaseMusic(music_backend)
        self.phase_name = '准备阶段'
        self.timer = Countdown(self.data[self.phase])
        self.display = Display(self)
        self.setWindowTitle('CRTC 配置与比赛控制')
        self.resize(940, 640)
        build_control_layout(self)
        apply_control_theme(self)
        self.start_shortcut = QShortcut(QKeySequence('Space'), self)
        self.start_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.start_shortcut.setAutoRepeat(False)
        self.start_shortcut.activated.connect(self.start_timer)
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
        data = self.data.copy()
        for key, field in self.fields.items():
            if isinstance(field, QCheckBox):
                data[key] = field.isChecked()
            elif isinstance(field, QComboBox):
                data[key] = field.currentText().strip()
            elif isinstance(field, QPlainTextEdit):
                data[key] = field.toPlainText().strip()[:10000 if key == 'messages' else 80]
            else:
                data[key] = field.text().strip() if isinstance(field, QLineEdit) else field.value()
        if any(not data[key] for key in ('title', 'match', 'left_team', 'right_team')):
            QMessageBox.warning(self, '配置未保存', '赛事名称、轮次和双方队伍不能为空。')
            return
        if not self.save_data(data):
            return
        reset_scroll = data['messages'] != self.data['messages']
        self.data = data
        if reset_scroll:
            self.display.reset_scroll()
        self.tick()

    def save_data(self, data):
        try:
            self.config_store.save(data)
        except OSError as exc:
            QMessageBox.warning(self, '保存失败', str(exc))
            return False
        return True

    def set_score(self, key, value):
        self.data[key] = bounded_score(value)
        field = self.score_fields[key]
        field.blockSignals(True)
        field.setValue(self.data[key])
        field.blockSignals(False)
        self.display.update()
        self.save_data(self.data)

    def import_teams(self):
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
        if self.timer.running:
            answer = QMessageBox.question(self, '重置计时', '计时正在进行，确定切换并重置倒计时？')
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.phase = phase
        self.music_phase = phase
        self.music.reset()
        self.phase_name = '准备阶段' if phase == 'preparation' else '正式比赛'
        self.timer.reset(self.data[phase])
        self.tick()

    def technical_pause(self):
        if self.phase != 'preparation':
            return
        self.phase_name = '技术暂停'
        self.music_phase = 'technical'
        self.music.reset()
        self.timer.reset(self.data['technical'])
        if self.data['technical_auto_start']:
            self.timer.start()
        self.tick()

    def toggle_timer(self):
        self.timer.pause() if self.timer.running else self.timer.start()
        self.tick()

    def start_timer(self):
        """空格开始或继续当前阶段；重复按下不会暂停正在运行的计时。"""
        self.timer.start()
        self.tick()

    def tick(self):
        if self.timer.finish_if_due():
            QApplication.beep()
        seconds = self.timer.seconds()
        self.music.sync(self.music_phase, self.timer.running, seconds)
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
        self.music.stop()
        QApplication.instance().quit()
        event.accept()
