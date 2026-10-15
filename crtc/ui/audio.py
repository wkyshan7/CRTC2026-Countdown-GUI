"""Qt 背景音乐：准备/技术暂停共用音源，循环播放并平滑调节音量。"""
from PySide6.QtCore import QObject, QUrl, QVariantAnimation, QEasingCurve, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from crtc.runtime import PROJECT_ROOT

FADE_DURATION_MS = 900
MUSIC_VOLUME = 0.65
PREPARATION_TRACK = PROJECT_ROOT / 'assets' / 'audio' / 'preparation.mp3'


class QtMusicBackend(QObject):
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
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(FADE_DURATION_MS)
        self.fade.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.fade.valueChanged.connect(self.output.setVolume)
        self.fade.finished.connect(self._finish_fade)

    def set_phase(self, phase):
        self.phase = phase
        if phase in ('preparation', 'technical'):
            source = QUrl.fromLocalFile(str(PREPARATION_TRACK))
            if self.player.source() != source:
                self.player.setSource(source)
        else:
            self.stop()

    def play(self):
        if self.phase not in ('preparation', 'technical'):
            return
        self.player.play()
        self._fade_to(MUSIC_VOLUME)

    def pause(self):
        self._fade_to(0.0, 'pause')

    def stop(self):
        self._fade_to(0.0, 'stop')

    def shutdown(self, callback):
        """退出时等待淡出完成，再结束应用。"""
        self._shutdown_callback = callback
        self.stop()

    def _fade_to(self, volume, action=None):
        # 从当前音量开始新过渡，快速暂停/继续时也不会跳变。
        self.fade.stop()
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
        action, self._pending_action = self._pending_action, None
        if action == 'pause':
            self.player.pause()
        elif action == 'stop':
            self.player.stop()
        if self._shutdown_callback is not None:
            callback, self._shutdown_callback = self._shutdown_callback, None
            callback()
