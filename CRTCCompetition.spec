# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""PyInstaller 构建：字体、图片和音乐作为内置资源随程序分发。"""

import os
from pathlib import Path

root = Path(SPECPATH)
onefile = os.environ.get('CRTC_BUILD_ONEFILE') == '1'
search_paths = [str(root)]
if (root / '.deps').is_dir():
    search_paths.append(str(root / '.deps'))

a = Analysis(
    [str(root / 'main.py')],
    pathex=search_paths,
    binaries=[],
    datas=[
        (str(root / 'assets' / 'font'), 'assets/font'),
        (str(root / 'assets' / 'images' / '*.png'), 'assets/images'),
        (str(root / 'assets' / 'images' / '*.ico'), 'assets/images'),
        (str(root / 'assets' / 'audio' / '*.mp3'), 'assets/audio'),
        (str(root / 'LICENSE'), '.'),
        (str(root / 'NOTICE.md'), '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    *([a.binaries, a.datas] if onefile else []),
    exclude_binaries=not onefile,
    name='CRTCCompetition',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / 'assets' / 'images' / 'app-icon.ico'),
)
if not onefile:
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CRTCCompetition')
