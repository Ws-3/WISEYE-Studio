import unittest
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from core.config import AppConfig
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.runtime_panel import EnvironmentDialog

ENV=dict(time_supported=True,fog_supported=True,rain_supported=True,time_override=False,hour=12,fog=0,rain=0)


class EnvironmentPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_no_support_no_apply_and_no_fake_hardware(self):
        window=MainWindow(AppConfig());dialog=EnvironmentDialog(window)
        try:
            self.assertFalse(dialog.apply.isEnabled())
            window.runtime_panel.update_state({})
            self.assertIn('未提供',window.runtime_panel.hardware.text())
        finally:dialog.close();window.close()
    def test_correlated_ack_and_waiting_lock(self):
        window=MainWindow(AppConfig());window.client.ready=True
        dialog=EnvironmentDialog(window)
        try:
            dialog.update_state(dict(run_id='a',environment=ENV));dialog.fog.setValue(80)
            self.assertTrue(dialog.apply.isEnabled())
            with patch.object(window.client,'request',return_value='mine') as send:
                dialog.submit(False)
                self.assertEqual(send.call_args.args[1]['fog'],.8)
            self.assertFalse(dialog.fog.isEnabled())
            dialog.completed('unrelated','environment.configure',{},dict(run_id='a',environment=ENV))
            self.assertEqual(dialog.pending,'mine')
            dialog.completed('mine','environment.configure',{},dict(run_id='a',environment=dict(ENV,fog=.8)))
            self.assertIsNone(dialog.pending);self.assertFalse(dialog.dirty)
            dialog.disconnected();self.assertFalse(dialog.apply.isEnabled())
        finally:dialog.close();window.close()
