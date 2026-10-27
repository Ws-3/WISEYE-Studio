import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from core.config import AppConfig
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.interface_settings import apply_config


class InterfaceSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_saved_settings_update_all_clients_and_source_table(self):
        window = MainWindow(AppConfig())
        try:
            config = replace(AppConfig(), rtsp_port=9554, airsim_port=50062,
                             rtsp_paths={'ptz-01/infrared':'test/thermal'})
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/'app.json'
                original_save = AppConfig.save
                with patch.object(AppConfig,'save',lambda c: original_save(c,path)):
                    apply_config(window,config)
                self.assertEqual(AppConfig.load(path),config)
                self.assertEqual(window.air_client.port,50062)
                self.assertEqual(window.client.config, config)
                addresses = [window.source_table.item(i,3).text() for i in range(window.source_table.rowCount())]
                self.assertIn('rtsp://127.0.0.1:9554/test/thermal',addresses)
        finally: window.close()

    def test_running_simulation_cannot_change_endpoints(self):
        window = MainWindow(AppConfig())
        try:
            window.runtime_manager = SimpleNamespace(running=True,processes=[])
            with patch.object(AppConfig,'save') as save, self.assertRaises(ValueError):
                apply_config(window, replace(AppConfig(),rtsp_port=9554))
            save.assert_not_called()
            del window.runtime_manager
        finally: window.close()


if __name__ == '__main__': unittest.main()
