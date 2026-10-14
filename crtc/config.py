"""默认值、配置兼容校验与 JSON 存储，不依赖图形界面。"""
import json
from copy import deepcopy
from pathlib import Path

from crtc.runtime import CONFIG_PATH

DEFAULTS = dict(title='重庆大学机器人训练大赛', match='决赛',
                left_team='你说得队', right_team='你说得队', left_score=0,
                right_score=0, preparation=120, technical=120, competition=240,
                english='FINAL\nMATCH', team_font_size=44, messages='', teams=[],
                technical_auto_start=True)

def bounded_score(value):
    return value if 0 <= value <= 3 else 0


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
                    data[key] = bounded_score(value)
                elif key == 'team_font_size':
                    data[key] = max(18, min(value, 90))
                else:
                    data[key] = max(1, min(value, 5999))
    except (OSError, ValueError, AttributeError):
        pass
    return data



class ConfigStore:
    """负责配置读取和原子写入；由调用方处理保存失败的提示。"""

    def __init__(self, path=CONFIG_PATH):
        self.path = Path(path)

    def load(self):
        return load_config(self.path)

    def save(self, data):
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)
