# SPDX-License-Identifier: GPL-3.0-or-later
"""将项目原始图片转换为 Windows 多尺寸 ICO，保留图案和背景。"""

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crtc.runtime import load_local_dependencies

load_local_dependencies()

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage

SIZES = (16, 24, 32, 48, 64, 128, 256)


def main():
    source = ROOT / 'assets' / 'images' / 'app-icon.jpg'
    destination = source.with_suffix('.ico')
    image = QImage(str(source))
    if image.isNull():
        raise RuntimeError(f'无法读取图标原图：{source}')
    image = image.convertToFormat(QImage.Format.Format_ARGB32)

    # ICO 目录后逐帧存放 PNG，以便 Windows 在不同 DPI 下选择合适分辨率。
    frames = []
    for size in SIZES:
        scaled = image.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not scaled.save(buffer, 'PNG'):
            raise RuntimeError(f'无法生成 {size}px 图标')
        frames.append(bytes(buffer.data()))

    offset = 6 + 16 * len(frames)
    output = bytearray(struct.pack('<HHH', 0, 1, len(frames)))
    for size, frame in zip(SIZES, frames):
        dimension = size if size < 256 else 0
        output.extend(
            struct.pack('<BBBBHHII', dimension, dimension, 0, 0, 1, 32, len(frame), offset)
        )
        offset += len(frame)
    output.extend(b''.join(frames))
    destination.write_bytes(output)
    print(f'已生成：{destination}')


if __name__ == '__main__':
    main()
