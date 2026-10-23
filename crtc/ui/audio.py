"""Qt 背景音乐：按阶段选曲、循环播放，并平滑切曲与调节音量。"""

from PySide6.QtCore import QObject, QUrl, QVariantAnimation, QEasingCurve, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from crtc.runtime import PROJECT_ROOT

FADE_DURATION_MS = 900
MUSIC_VOLUME = 0.65
PREPARATION_TRACK = PROJECT_ROOT / 'assets' / 'audio' / 'preparation.mp3'
COMPETITION_TRACK = PROJECT_ROOT / 'assets' / 'audio' / 'competition.mp3'
PHASE_TRACKS = {
    'preparation': PREPARATION_TRACK,
    'technical': PREPARATION_TRACK,
    'competition': COMPETITION_TRACK,
}


class QtMusicBackend(QObject):
    """持有单个播放器；动画结束后才真正执行暂停或停止。"""

    error = Signal(str)

    def __init__(self, parent=None, *, player=None, output=None):
        super().__init__(parent)
        self.player = player if player is not None else QMediaPlayer(self)
        self.output = output if output is not None else QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.output.setVolume(0)
        self.player.errorOccurred.connect(lambda *_: self.error.emit(self.player.errorString()))
        self.phase = None
        self._pending_action = None
        self._shutdown_callback = None
        self._next_source = None
        self._want_playing = False
        self.volume = MUSIC_VOLUME

        # 动画在 GUI 事件循环推进，不使用 sleep 阻塞计时或界面。
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(FADE_DURATION_MS)
        self.fade.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.fade.valueChanged.connect(self.output.setVolume)
        self.fade.finished.connect(self._finish_fade)

    def set_phase(self, phase):
        """同源保持播放位置，换曲先淡出，静音后才替换音源。"""
        self.phase = phase
        track = PHASE_TRACKS.get(phase)
        if track is None:
            self._next_source = None
            self.stop()
            return
        source = QUrl.fromLocalFile(str(track))
        if self.player.source() == source:
            self._next_source = None
            return
        self._next_source = source
        self._want_playing = False
        self._fade_to(0.0, 'switch')

    def play(self):
        if self.phase not in PHASE_TRACKS:
            return
        self._want_playing = True
        if self._next_source is not None:
            self._fade_to(0.0, 'switch')
            return
        self.player.play()
        self._fade_to(self.volume)

    def pause(self):
        self._want_playing = False
        self._fade_to(0.0, 'pause')

    def stop(self):
        self._want_playing = False
        self._fade_to(0.0, 'stop')

    def set_volume(self, percent):
        """保存目标增益；切曲、暂停或停止的淡出不被音量调整打断。"""
        self.volume = max(0, min(percent, 100)) / 100.0
        if self._want_playing and self._pending_action not in ('switch', 'pause', 'stop'):
            self._fade_to(self.volume)

    def shutdown(self, callback):
        """退出时等待淡出完成，再结束应用。"""
        self._shutdown_callback = callback
        self.stop()

    def _fade_to(self, volume, action=None):
        # 从当前音量开始新过渡，快速暂停/继续时也不会跳变。
        self.fade.stop()

        # 新操作替换旧的结束动作，防止继续播放后又被旧动画暂停。
        self._pending_action = action
        current = self.output.volume()
        if abs(current - volume) < 0.001:
            self.output.setVolume(volume)
            self._finish_fade()
            return

        self.fade.setStartValue(float(current))
        self.fade.setEndValue(float(volume))
        self.fade.start()

    def _finish_fade(self):
        """先完成播放器动作，再通知等待退出的应用。"""
        action, self._pending_action = self._pending_action, None
        if action == 'pause':
            self.player.pause()
        elif action == 'stop':
            self.player.stop()

        if self._next_source is not None:
            source, self._next_source = self._next_source, None
            self.player.setSource(source)
            if self._want_playing:
                self.player.play()
                self._fade_to(self.volume)

        if self._shutdown_callback is not None:
            callback, self._shutdown_callback = self._shutdown_callback, None
            callback()
