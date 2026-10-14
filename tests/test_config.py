"""配置迁移、容错和存储验证，无需创建 Qt 应用。"""
import tempfile
import unittest
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()
