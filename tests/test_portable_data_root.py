import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PortableDataRootTests(unittest.TestCase):
    def test_portable_directory_moves_with_release_and_preserves_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            release=Path(folder)/'first-drive-folder';release.mkdir()
            (release/'portable.flag').write_text('portable')
            resources=release/'Resources/configs';resources.mkdir(parents=True)
            (resources/'app.json').write_text('{"preserved":false}')
            def inspect(root):
                env=dict(os.environ,WISEYE_RELEASE_ROOT=str(root))
                env.pop('WISEYE_DATA_DIR',None);env.pop('WISEYE_RESOURCES_DIR',None)
                code='from core.runtime_paths import DATA_ROOT,initialize_data;initialize_data();print(DATA_ROOT)'
                return Path(subprocess.check_output([sys.executable,'-c',code],env=env,text=True).strip())
            data=inspect(release);self.assertEqual(data,release/'UserData')
            (data/'configs/app.json').write_text('{"preserved":true}')
            moved=Path(folder)/'different-drive-folder';release.rename(moved)
            self.assertEqual(inspect(moved),moved/'UserData')
            self.assertTrue(json.loads((moved/'UserData/configs/app.json').read_text())['preserved'])


if __name__=='__main__':unittest.main()
