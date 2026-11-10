import unittest
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.main_window import MainWindow
from core.config import AppConfig
from tests.verify_observation_ui import state


class SensorUpgradeUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow(AppConfig());self.w.state=state();self.w.client.ready=True
        self.sync=patch.object(self.w.gallery,'sync_clients');self.sync.start()
        self.sender=patch.object(self.w.client,'request',return_value='read');self.send=self.sender.start()
    def tearDown(self):
        self.w.client.ready=False;self.w.close();self.sender.stop();self.sync.stop()
    def test_pair_is_left_right_with_optional_scene(self):
        m=self.w.mission_workspace;m.panel.refresh_devices(state());m.open_aerial('uav-01')
        m.modality.setCurrentIndex(m.modality.findData('both'))
        for ref in [False,True]:
            m.reference.setChecked(ref);m.camera_changed(force=True)
            positions=[self.w.gallery.grid.getItemPosition(self.w.gallery.grid.indexOf(self.w.gallery.cards['uav-01/'+s]))[:2] for s in ['aerial','aerial_infrared']]
            self.assertEqual(positions,[(0,0),(0,1)])
    def test_old_aerial_does_not_send_focus_fields(self):
        p=self.w.mission_workspace.panel;p.refresh_devices(state());p.pending='read';p.completed('read','aerial.get_state',{},state())
        self.assertNotIn('focus_mode',p.values());self.assertFalse(p.fields['focus_mode'].isEnabled())
    def test_new_camera_has_manual_lens_controls(self):
        s=state()
        for d in s['devices']:d['aerial'].update(focus_supported=True,focus_mode='manual',focus_distance_m=42,aperture_f=4,vis_blur_px=.95)
        p=self.w.mission_workspace.panel;p.refresh_devices(s);p.pending='read';p.completed('read','aerial.get_state',{},s)
        self.assertEqual(p.values()['focus_mode'],'manual');self.assertEqual(p.values()['focus_distance_m'],42)
        self.assertTrue(p.fields['focus_distance_m'].isEnabled())
    def test_window_button_is_one_reversible_command(self):
        self.w.engine_window_button.setEnabled(True)
        self.w.engine_window_button.setChecked(True);self.w.engine_window_button.setChecked(False)
        calls=[c.args for c in self.send.call_args_list if c.args[0]=='sim.window.set_visible']
        self.assertEqual(calls,[('sim.window.set_visible',{'visible':True}),('sim.window.set_visible',{'visible':False})])


if __name__=='__main__':unittest.main()
