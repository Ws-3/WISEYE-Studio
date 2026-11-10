import unittest
import json
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.main_window import MainWindow
from core.config import AppConfig
from tests.verify_observation_ui import state


class MissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow(AppConfig());self.w.state=state();self.m=self.w.mission_workspace
        self.m.panel.refresh_devices(state());self.w.client.ready=True
        self.sync=patch.object(self.w.gallery,'sync_clients');self.sync.start()
        self.request=patch.object(self.w.client,'request',return_value='read');self.send=self.request.start()
        self.flight=patch.object(self.w.air_client,'request');self.fly=self.flight.start()
    def tearDown(self):
        self.w.client.ready=False;self.w.close();self.flight.stop();self.request.stop();self.sync.stop()
    def test_aerial_is_embedded_and_does_not_take_over_flight(self):
        selected=self.w.selected_drone;self.m.open_aerial('uav-02')
        self.assertFalse(self.m.panel.isWindow());self.assertEqual(self.w.inspectors.currentIndex(),3)
        self.assertEqual(self.w.gallery.sources,['uav-02/aerial']);self.assertTrue(self.w.tree_panel.isHidden())
        self.assertEqual(self.w.selected_drone,selected);self.fly.assert_not_called()
        self.assertTrue(all(c.args[0]=='aerial.get_state' for c in self.send.call_args_list))
    def test_layout_restore_reference_and_camera_switch(self):
        initial=(list(self.w.gallery.sources),self.w.gallery.mode)
        self.m.open_aerial('uav-01');self.m.reference.setChecked(True)
        saved=json.loads(self.w.gallery.settings.value('workspace/v3'))
        self.assertEqual((saved['sources'],saved['mode']),initial)
        self.assertEqual(self.w.gallery.sources,['uav-01/aerial','scene/observer'])
        self.m.panel.device.setCurrentIndex(self.m.panel.device.findData('uav-02'))
        self.assertEqual(self.w.gallery.sources,['uav-02/aerial','scene/observer'])
        self.m.choose('observation')
        self.assertEqual((self.w.gallery.sources,self.w.gallery.mode),initial)
        self.assertFalse(self.m.panel.aim_queued);self.assertFalse(self.w.tree_panel.isHidden())
    def test_capture_is_disabled_without_a_current_frame(self):
        self.m.open_aerial('uav-01');self.m.observe(state());self.assertFalse(self.m.capture.isEnabled())
        self.w.client.ready=False;self.m.connection(False);self.assertFalse(self.m.capture.isEnabled())

    def test_context_keyboard_and_fullscreen(self):
        from PySide6.QtCore import Qt,QEvent
        from PySide6.QtGui import QKeyEvent
        self.assertTrue(self.w.context_group.button(3).isHidden())
        self.m.open_aerial('uav-01');self.assertFalse(self.w.context_group.button(3).isHidden())
        self.m.panel.pending='read';self.m.panel.completed('read','aerial.get_state',{},state())
        start=self.m.panel.fields['pitch_deg'].value()
        self.m.handle_key(QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Up,Qt.KeyboardModifier.NoModifier))
        self.m.key_step();self.assertGreater(self.m.panel.fields['pitch_deg'].value(),start)
        self.m.handle_key(QKeyEvent(QEvent.Type.KeyRelease,Qt.Key.Key_Up,Qt.KeyboardModifier.NoModifier))
        self.assertFalse(self.m.key_timer.isActive());self.m.choose('observation');self.assertFalse(self.m.aim_keys)
        self.w.fullscreen_action.setChecked(True);self.assertTrue(self.w.isFullScreen())
        self.w.fullscreen_action.setChecked(False);self.assertTrue(self.w.isMaximized())

if __name__=='__main__':unittest.main()
