"""项目路径与可选的本地依赖加载。"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_config_path():
    """源码沿用项目配置；EXE 使用用户目录，避免安装目录只读或资源被解包覆盖。"""
    if getattr(sys, 'frozen', False):
        local_data = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        return local_data / 'CRTCCompetition' / 'config.json'
    return PROJECT_ROOT / 'config.json'


CONFIG_PATH = get_config_path()


def load_local_dependencies():
    if getattr(sys, 'frozen', False):
        return

    local_deps = PROJECT_ROOT / '.deps'
    if local_deps.is_dir() and str(local_deps) not in sys.path:
        sys.path.insert(0, str(local_deps))
