import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ReleasePathsTests(unittest.TestCase):
    def test_separate_read_only_resources_preserve_user_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            install = base / '安装 空格'
            resources = install / 'Resources'
            config = resources / 'configs/app.json'
            config.parent.mkdir(parents=True)
            config.write_text('{"first": true}', encoding='utf-8')
            (install / 'release.json').write_text(json.dumps({'scenes': ['city']}), encoding='utf-8')
            data = base / '用户数据'
            environment = dict(os.environ, WISEYE_RELEASE_ROOT=str(install), WISEYE_DATA_DIR=str(data))
            code = "from core.runtime_paths import *; initialize_data(); assert installed_scenes()=={'city'}; assert DATA_ROOT!=INSTALL_ROOT"
            subprocess.run([sys.executable, '-X', 'utf8', '-c', code], env=environment, check=True)
            target = data / 'configs/app.json'
            self.assertEqual(target.read_text(), '{"first": true}')
            target.write_text('{"user": true}', encoding='utf-8')
            subprocess.run([sys.executable, '-X', 'utf8', '-c', code], env=environment, check=True)
            self.assertEqual(target.read_text(), '{"user": true}')
            self.assertEqual(config.read_text(), '{"first": true}')

    def test_packaged_scenes_do_not_require_editor_umap_files(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / 'release.json').write_text('{"scenes":["city"]}', encoding='utf-8')
            environment = dict(os.environ, WISEYE_RELEASE_ROOT=str(base), WISEYE_DATA_DIR=str(base / 'Data'))
            code = "from core.runtime_paths import installed_scenes; assert installed_scenes()=={'city'}"
            subprocess.run([sys.executable, '-c', code], env=environment, check=True)


if __name__ == '__main__':
    unittest.main()
