"""配置迁移、容错和存储验证，无需创建 Qt 应用。"""
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from crtc.config import ConfigStore
from crtc.runtime import PROJECT_ROOT


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=PROJECT_ROOT)
        self.store = ConfigStore(Path(self.directory.name) / 'config.json')

    def tearDown(self):
        self.directory.cleanup()

    def test_old_config_preserves_existing_values_and_adds_defaults(self):
        self.store.path.write_text('{"left_score": 2, "preparation": 180}', encoding='utf-8')
        data = self.store.load()
        self.assertEqual(data['left_score'], 2)
        self.assertEqual(data['preparation'], 180)
        self.assertEqual(data['team_font_size'], 44)
        self.assertEqual(data['teams'], [])

    def test_missing_or_corrupt_config_uses_independent_defaults(self):
        first = self.store.load()
        first['teams'].append('临时队伍')
        self.assertEqual(self.store.load()['teams'], [])
        self.store.path.write_text('invalid json', encoding='utf-8')
        self.assertEqual(self.store.load()['competition'], 240)

    def test_roundtrip_unicode_and_multiline(self):
        data = self.store.load()
        data['messages'] = '第一条\n第二条'
        data['teams'] = ['红队', '蓝队']
        self.store.save(data)
        self.assertEqual(self.store.load(), data)
        self.assertFalse(self.store.path.with_suffix('.json.tmp').exists())

    def test_invalid_ranges_are_normalized(self):
        self.store.path.write_text(
            '{"left_score": 8, "team_font_size": 1000, "technical": -1}', encoding='utf-8')
        data = self.store.load()
        self.assertEqual(data['left_score'], 0)
        self.assertEqual(data['team_font_size'], 90)
        self.assertEqual(data['technical'], 1)

    def test_temporary_replace_lock_is_retried(self):
        import os
        replace = os.replace
        data = self.store.load()
        with patch('crtc.config.os.replace') as mocked:
            def retry(source, destination):
                if mocked.call_count == 1:
                    raise PermissionError('locked')
                replace(source, destination)
            mocked.side_effect = retry
            with patch('crtc.config.time.sleep'):
                self.store.save(data)
        self.assertEqual(self.store.load(), data)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(list(self.store.path.parent.glob('*.tmp')), [])

    def test_replace_denied_falls_back_and_preserves_backup(self):
        old = self.store.load()
        old['messages'] = '较长的旧信息' * 20
        self.store.save(old)
        new = dict(old, messages='新信息', left_score=2)
        with (patch('crtc.config.os.replace', side_effect=PermissionError('denied')),
              patch('crtc.config.time.sleep')):
            self.store.save(new)
        self.assertEqual(self.store.load(), new)
        self.assertEqual(self.store.path.with_suffix('.json.bak').read_bytes(),
                         json.dumps(old, ensure_ascii=False, indent=2).encode('utf-8'))
        self.assertEqual(list(self.store.path.parent.glob('*.tmp')), [])

    def test_failure_keeps_original_config_and_cleans_temporary_file(self):
        data = self.store.load()
        self.store.save(data)
        original = self.store.path.read_bytes()
        with (patch('crtc.config.os.replace', side_effect=PermissionError('denied')),
              patch('crtc.config.time.sleep'),
              patch.object(self.store, '_overwrite_existing', side_effect=PermissionError('read only'))):
            with self.assertRaises(PermissionError):
                self.store.save(dict(data, left_score=3))
        self.assertEqual(self.store.path.read_bytes(), original)
        self.assertEqual(list(self.store.path.parent.glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
