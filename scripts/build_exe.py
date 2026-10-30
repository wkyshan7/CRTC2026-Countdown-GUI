# SPDX-License-Identifier: GPL-3.0-or-later
"""在 Windows 构建可分发程序：默认目录版，--onefile 为单文件版。"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onefile', action='store_true', help='构建单文件 EXE')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows EXE 请在 Windows 环境中构建。')

    # 本机可复用隔离安装的工具；其他电脑可按 requirements-build.txt 安装。
    paths = [str(ROOT / name) for name in ('.devtools', '.deps') if (ROOT / name).is_dir()]
    environment = os.environ.copy()
    # 避免 PATH 中其他工具链的同名 Qt/ICU DLL 被错误打进分发包。
    windows = Path(environment.get('SystemRoot', r'C:\Windows'))
    environment['PATH'] = os.pathsep.join(
        str(path)
        for path in (
            Path(sys.executable).parent,
            Path(sys.base_prefix),
            Path(sys.base_prefix) / 'DLLs',
            windows / 'System32',
            windows,
        )
        if path.is_dir()
    )
    if paths:
        environment['PYTHONPATH'] = os.pathsep.join(paths + [environment.get('PYTHONPATH', '')])
    environment['CRTC_BUILD_ONEFILE'] = '1' if args.onefile else '0'

    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--distpath',
        str(ROOT / 'dist'),
        '--workpath',
        str(ROOT / 'build'),
        str(ROOT / 'CRTCCompetition.spec'),
    ]
    result = subprocess.run(command, cwd=ROOT, env=environment)
    if result.returncode == 0:
        output = (
            ROOT
            / 'dist'
            / ('CRTCCompetition.exe' if args.onefile else 'CRTCCompetition/CRTCCompetition.exe')
        )
        print(f'构建完成：{output}')
        if not args.onefile:
            print('分发时请打包整个 dist/CRTCCompetition 文件夹，不能只复制 EXE。')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
