"""Meaningful install preflight tests: user assets, traversal, and repeat installs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('wiseye_install', Path(__file__).resolve().parents[1] / 'packaging/install_plugin.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PluginInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        self.host = self.root / 'host'
        self.host.mkdir()
        self.project = self.host / 'Host.uproject'
        self.project.write_text(json.dumps({'FileVersion': 3, 'Modules': [{'Name': 'Host'}],
                                             'Plugins': [{'Name': 'Other', 'Enabled': True}]}))
        self.relative = 'Plugins/WISEYE/WISEYE.uplugin'
        source = self.bundle / 'payload' / self.relative
        source.parent.mkdir(parents=True)
        source.write_text('{}')
        self.files = {self.relative: hashlib.sha256(source.read_bytes()).hexdigest()}
        self.manifest()

    def manifest(self):
        (self.bundle / 'bundle.json').write_text(json.dumps({'files': self.files}))

    def run_install(self, apply=False):
        return installer.install(self.bundle, self.project, 'custom', '/Game/Maps/Test', apply)

    def test_preflight_does_not_write(self):
        before = self.project.read_bytes()
        self.assertFalse(self.run_install()['applied'])
        self.assertEqual(before, self.project.read_bytes())
        self.assertFalse((self.host / 'Plugins').exists())

    def test_user_asset_conflict_aborts_before_changes(self):
        target = self.host / self.relative
        target.parent.mkdir(parents=True)
        target.write_text('user content')
        with self.assertRaises(FileExistsError):
            self.run_install(True)
        self.assertEqual(target.read_text(), 'user content')
        self.assertFalse((self.host / 'Config').exists())

    def test_install_repeat_preserves_user_configuration(self):
        self.run_install(True)
        scene = self.host / 'Config/WISEYE/Scenes/custom.json'
        data = json.loads(scene.read_text()); data['gimbal_location_cm'] = [100, 200, 300]
        scene.write_text(json.dumps(data))
        self.run_install(True)
        self.assertEqual(json.loads(scene.read_text())['gimbal_location_cm'], [100, 200, 300])
        self.assertIn({'Name': 'Other', 'Enabled': True}, json.loads(self.project.read_text())['Plugins'])
        self.assertTrue(self.project.with_suffix('.uproject.before-wiseye').exists())

    def test_traversal_rejected(self):
        self.files['../outside'] = 'bad'
        self.manifest()
        with self.assertRaises(ValueError):
            self.run_install(True)
        self.assertFalse((self.host / 'Config').exists())

    def test_incompatible_engine_setting_rejected(self):
        config = self.host / 'Config/DefaultEngine.ini'
        config.parent.mkdir();config.write_text('[/Script/Engine.RendererSettings]\nr.CustomDepth=1\n')
        with self.assertRaises(ValueError):
            self.run_install(True)
        self.assertFalse((self.host / 'Plugins').exists())

    def test_missing_or_corrupt_payload_rejected(self):
        (self.bundle / 'payload' / self.relative).write_text('corrupt')
        with self.assertRaises(ValueError):
            self.run_install(True)

    def test_case_insensitive_host_module_collision_rejected(self):
        self.project.write_text(json.dumps({'Modules': [{'Name': 'Test'}]}))
        with self.assertRaisesRegex(ValueError, 'module test'):
            self.run_install(True)
        self.assertFalse((self.host / 'Plugins').exists())

    def test_custom_host_packaging_keeps_user_settings_and_dynamic_assets(self):
        game = self.host / 'Config/DefaultGame.ini'
        game.parent.mkdir()
        original = '[UserSettings]\nExperiment=original\n'
        game.write_text(original)
        self.run_install(True)
        self.run_install(True)
        content = game.read_text()
        self.assertTrue(content.startswith(original))
        self.assertEqual(content.count('; WISEYE dynamic sensor and vehicle assets'), 1)
        self.assertIn('/Game/WISEYE/Sensors', content)
        self.assertIn('/Game/WISEYE/DroneModels', content)


if __name__ == '__main__':
    unittest.main()
