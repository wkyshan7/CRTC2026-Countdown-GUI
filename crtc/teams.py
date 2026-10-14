"""TXT 队伍名单解码、校验与去重。"""

def parse_teams(raw):
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('请使用 UTF-8 或 GBK 编码的 TXT 文件。')
    names = list(dict.fromkeys(line.strip() for line in content.splitlines() if line.strip()))
    if not names:
        raise ValueError('文件中没有队伍名称。')
    if any(len(name) > 80 for name in names):
        raise ValueError('每个队伍名称最多 80 个字符。')
    return names
