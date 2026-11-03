"""Desktop startup stages and single automatic connection, no real processes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from core.config import AppConfig
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.startup_status import StartupStatus


class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_stages_connect_once_and_failure_is_visible(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{'WISEYE_SESSION_STATUS':''}):
            w=MainWindow(AppConfig.load())
            try:
                path=Path(folder)/'startup.json';watch=StartupStatus(w,path)
                with patch.object(w,'connect_ue') as connect:
                    for stage,text in [('loading','UE loading'),('flight','flight loading'),('assets','Preparing assets'),('ready','ready')]:
                        path.write_text(json.dumps(dict(stage=stage,message=text)))
                        watch.poll();self.assertIn(text,w.logs.toPlainText())
                        if stage!='ready':self.assertFalse(w.quick_connect.isEnabled())
                    watch.poll();connect.assert_called_once()
                    self.assertFalse(watch.timer.isActive())
                    path.write_text(json.dumps(dict(stage='failed',message='worker exited')))
                    watch.poll();self.assertEqual(w.badge.text(),'启动失败 · 连接')
                    self.assertIn('worker exited',w.connection_detail.text())
            finally:w.close();self.app.processEvents()
