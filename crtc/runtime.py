"""项目路径与可选的本地依赖加载。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config.json'


def load_local_dependencies():
    local_deps = PROJECT_ROOT / '.deps'
    if local_deps.is_dir() and str(local_deps) not in sys.path:
        sys.path.insert(0, str(local_deps))
