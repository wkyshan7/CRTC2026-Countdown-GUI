"""验证源码和 EXE 的资源/配置路径策略。"""

import os
import sys
import unittest
from unittest.mock import patch

from crtc.runtime import PROJECT_ROOT, get_config_path


class RuntimeTests(unittest.TestCase):
    def test_source_keeps_existing_project_config(self):
        with patch.object(sys, 'frozen', False, create=True):
            self.assertEqual(get_config_path(), PROJECT_ROOT / 'config.json')

    def test_executable_config_is_persistent_user_data(self):
        with (
            patch.object(sys, 'frozen', True, create=True),
            patch.dict(os.environ, {'LOCALAPPDATA': str(PROJECT_ROOT / 'test-user-data')}),
        ):
            self.assertEqual(
                get_config_path(),
                PROJECT_ROOT / 'test-user-data' / 'CRTCCompetition' / 'config.json',
            )


if __name__ == '__main__':
    unittest.main()
