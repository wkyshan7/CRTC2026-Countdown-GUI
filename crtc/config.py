"""默认值、配置兼容校验与 JSON 存储，不依赖图形界面。"""
import json
import os
import tempfile
import time
from copy import deepcopy
from pathlib import Path

from crtc.runtime import CONFIG_PATH

DEFAULTS = dict(title='重庆大学机器人训练大赛', match='决赛',
                left_team='你说得队', right_team='你说得队', left_score=0,
                right_score=0, preparation=120, technical=120, competition=240,
                english='FINAL\nMATCH', team_font_size=44, messages='', teams=[],
                technical_auto_start=True, score_limit=3)

def bounded_score(value, limit=3):
    return value if 0 <= value <= limit else 0


def load_config(path=CONFIG_PATH):
    data = deepcopy(DEFAULTS)
    try:
        saved = json.loads(Path(path).read_text(encoding='utf-8'))
        for key, default in DEFAULTS.items():
            value = saved.get(key, default)
            if isinstance(default, bool):
                if type(value) is bool:
                    data[key] = value
            elif isinstance(default, str) and isinstance(value, str):
                data[key] = value[:10000 if key == 'messages' else 80]
            elif key == 'teams' and isinstance(value, list):
                data[key] = list(dict.fromkeys(v.strip()[:80] for v in value if isinstance(v, str) and v.strip()))
            elif type(value) is int:
                if key.endswith('_score'):
                    data[key] = value
                elif key == 'score_limit':
                    data[key] = max(1, min(value, 99))
                elif key == 'team_font_size':
                    data[key] = max(18, min(value, 90))
                else:
                    data[key] = max(1, min(value, 5999))
    except (OSError, ValueError, AttributeError):
        pass
    for key in ('left_score', 'right_score'):
        data[key] = bounded_score(data[key], data['score_limit'])
    return data



class ConfigStore:
    """优先原子替换；Windows 禁止替换时，备份后写入现有文件。"""

    def __init__(self, path=CONFIG_PATH):
        self.path = Path(path)

    def load(self):
        return load_config(self.path)

    def save(self, data):
        content = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        temporary = None
        try:
            # 每次使用独立临时文件，避免多个程序实例共享同一个 .tmp。
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=self.path.name + '.',
                                             suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            for attempt in range(3):
                try:
                    os.replace(temporary, self.path)
                    return
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.05 * (attempt + 1))
                    elif self.path.is_file():
                        self._overwrite_existing(content)
                    else:
                        raise
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def _overwrite_existing(self, content):
        """有写权限但没有替换权限时保留文件本身；旧内容备份便于恢复。"""
        original = self.path.read_bytes()
        backup = self.path.with_suffix(self.path.suffix + '.bak')
        backup.write_bytes(original)
        # r+b 不会在打开时截断，权限不足时原配置保持完整。
        with self.path.open('r+b') as stream:
            try:
                stream.write(content)
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())
            except OSError:
                try:
                    stream.seek(0)
                    stream.write(original)
                    stream.truncate()
                    stream.flush()
                    os.fsync(stream.fileno())
                except OSError:
                    pass  # 旧内容仍保存在 .bak 文件中。
                raise
