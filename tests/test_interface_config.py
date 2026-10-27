import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from core.config import AppConfig
from apps.desktop_app.source_registry import Source


class InterfaceConfigTests(unittest.TestCase):
    def test_old_config_and_multi_device_defaults(self):
        config = AppConfig()
        self.assertEqual(config.stream_path('ptz-02','visible'), 'ptz-02/CH1')
        self.assertEqual(config.stream_path('scene','observer'), 'OBS')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'app.json'
            path.write_text('{"rtsp_port": 9554}', encoding='utf8')
            self.assertEqual(AppConfig.load(path).rtsp_port, 9554)

    def test_override_roundtrip_and_shared_display(self):
        config = replace(AppConfig(), rtsp_host='192.168.1.20', rtsp_port=9554,
                         rtsp_paths={'ptz-02/infrared':'camera2/thermal','scene/observer':'world'})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'app.json'; config.save(path)
            loaded = AppConfig.load(path)
            self.assertEqual(loaded, config)
            self.assertEqual(Source('ptz-02','infrared').url('unused',loaded),
                             'rtsp://192.168.1.20:9554/camera2/thermal')
            self.assertEqual(loaded.stream_path('ptz-01','infrared'),'CH2')

    def test_reject_collision_invalid_path_and_invalid_host(self):
        for changes in [dict(rtsp_visible_path='CH2'), dict(rtsp_port=50051),
                        dict(rtsp_host='rtsp://localhost'), dict(rtsp_visible_path='../a'),
                        dict(rtsp_paths={'ptz-03/visible':'CH1'}), dict(rtsp_paths=[]),
                        dict(rtsp_paths={'uav-01/visible':'uav'})]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(AppConfig(), **changes).validate()

    def test_writable_mediamtx_matches_port(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'logs/runtime.yml'
            replace(AppConfig(),rtsp_port=9554).write_mediamtx(path)
            values=json.loads(path.read_text())
            self.assertEqual(values['rtspAddress'], ':9554')
            self.assertEqual(values['paths']['all_others']['source'], 'publisher')


if __name__ == '__main__': unittest.main()
