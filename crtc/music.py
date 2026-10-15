"""阶段背景音乐接口和状态同步；具体播放由界面层实现。"""

from typing import Literal, Protocol

MusicPhase = Literal['preparation', 'technical', 'competition']


class MusicBackend(Protocol):
    """后续播放器实现此接口；set_phase 负责选曲，play 负责播放或继续。"""

    def set_phase(self, phase: MusicPhase) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def stop(self) -> None: ...


class SilentMusicBackend:
    """未接入背景音乐时的默认实现。"""

    def set_phase(self, phase: MusicPhase) -> None:
        pass

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass


class PhaseMusic:
    """将计时状态转换为播放器事件，避免每次界面刷新重复播放。"""

    def __init__(self, backend: MusicBackend | None = None):
        self.backend = backend if backend is not None else SilentMusicBackend()
        self.phase = None
        self.state = 'stopped'
        self.enabled = True

    def set_enabled(self, enabled: bool):
        """切换音乐开关；重新开启后由下一次状态同步决定是否播放。"""
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.stop()

    def reset(self):
        """重置或覆盖计时时，让下一次同步重新选曲并从头播放。"""
        self.stop()
        self.phase = None

    def sync(self, phase: MusicPhase, running: bool, remaining: int):
        """仅在目标状态变化时发出播放指令，避免刷新循环重启音源。"""
        if phase != self.phase:
            # 准备和技术暂停共用曲目，阶段切换不停止、不重新播放。
            continuous = {self.phase, phase} <= {'preparation', 'technical'}
            if self.phase is not None and not continuous:
                self.stop()
            self.backend.set_phase(phase)
            self.phase = phase

        # 关闭音乐仍更新选曲阶段，重新开启时能恢复到正确音源。
        if not self.enabled:
            return

        target = 'playing' if running else ('stopped' if remaining == 0 else 'paused')
        if target == self.state:
            return

        if target == 'playing':
            self.backend.play()
        elif target == 'paused' and self.state == 'playing':
            self.backend.pause()
        elif target == 'stopped':
            self.backend.stop()
        self.state = target

    def stop(self):
        self.backend.stop()
        self.state = 'stopped'
