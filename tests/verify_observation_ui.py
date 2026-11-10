import unittest
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.observation_panel import ObservationDialog
from apps.desktop_app.source_registry import Source
from core.config import AppConfig

CAM=dict(enabled=True,stabilized=True,pitch_deg=-60,yaw_deg=0,fov_deg=65,sample_hz=15)
def state():return dict(run_id='one',devices=[dict(id='uav-01',kind='drone',name='First',aerial=dict(CAM)),dict(id='uav-02',kind='drone',name='Second',aerial=dict(CAM))],population=dict(vehicles_enabled=True,pedestrians_enabled=True,vehicle_density=.25,pedestrian_density=.5,vehicles_supported=True,pedestrians_supported=True,pending=False))

class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow(AppConfig());self.w.state=state();self.w.client.ready=True;self.dialogs=[]
    def tearDown(self):
        for d in self.dialogs:d.close()
        self.w.client.ready=False;self.w.close()
    def dialog(self,aerial):
        d=ObservationDialog(self.w,aerial);self.dialogs.append(d);return d
    def fill(self,d):
        d.pending='load';d.completed('load','aerial.get_state' if d.aerial else 'population.get_state',{},state())
    def test_no_commands_before_read_and_addressed_preset(self):
        d=self.dialog(True);self.assertFalse(d.apply.isEnabled());self.fill(d)
        with patch.object(self.w.client,'request',return_value='mine') as send,patch.object(self.w.air_client,'request') as flight:
            d.preset(-90);self.assertEqual(send.call_args.args[0],'aerial.configure');self.assertEqual(send.call_args.args[1]['device_id'],'uav-01')
            self.assertEqual(send.call_args.args[1]['pitch_deg'],-90);flight.assert_not_called()
        self.assertFalse(d.apply.isEnabled());d.completed('other','aerial.configure',{},state());self.assertEqual(d.pending,'mine')
    def test_density_normalized_and_save_requires_applied_state(self):
        d=self.dialog(False);self.fill(d);d.fields['vehicle_density'].setValue(70)
        self.assertFalse(d.save.isEnabled())
        with patch.object(self.w.client,'request',return_value='set') as send:
            d.submit();self.assertEqual(send.call_args.args[1]['vehicle_density'],.7)
        d.completed('set','population.configure',{},state());self.assertTrue(d.save.isEnabled())
    def test_old_camera_ack_cannot_change_new_device(self):
        d=self.dialog(True);self.fill(d)
        with patch.object(self.w.client,'request',return_value='new'):
            d.pending='old';d.device.setCurrentIndex(1)
        d.completed('old','aerial.configure',{},state());self.assertEqual(d.pending,'new');self.assertFalse(d.valid)
    def test_disconnection_and_scene_change_invalidate_controls(self):
        d=self.dialog(True);self.fill(d);d.observe(dict(run_id='two',devices=state()['devices']))
        self.assertFalse(d.valid);self.assertFalse(d.preview.isEnabled())
        self.fill(d);self.w.client.ready=False;d.connection(False);self.assertFalse(d.apply.isEnabled())
    def test_aerial_has_no_fake_rtsp_endpoint(self):
        self.assertEqual(Source.parse('uav-02/aerial').url('localhost',AppConfig()),'')

    def test_continuous_aim_keeps_latest_edit_across_ack(self):
        d=self.dialog(True);self.fill(d);d.show()
        with patch.object(self.w.client,'request',side_effect=['first','latest']) as send:
            d.nudge('yaw_deg',2);d.flush_aim();self.assertEqual(send.call_count,1)
            self.assertTrue(d.fields['yaw_deg'].isEnabled())
            for _ in range(10):d.nudge('yaw_deg',2);d.flush_aim()
            self.assertEqual(send.call_count,1)
            ack=state();ack['devices'][0]['aerial']['yaw_deg']=2
            d.completed('first','aerial.configure',{},ack)
            self.assertEqual(d.fields['yaw_deg'].value(),22)
            d.flush_aim();self.assertEqual(send.call_count,2)
            self.assertEqual(send.call_args.args[1]['yaw_deg'],22)
            d.live_aim.setChecked(False);d.nudge('yaw_deg',2)
            d.completed('latest','aerial.configure',{},ack);d.flush_aim()
            self.assertEqual(d.fields['yaw_deg'].value(),24);self.assertTrue(d.dirty);self.assertEqual(send.call_count,2)
            d.connection(False);d.flush_aim();self.assertEqual(send.call_count,2)

    def test_manual_aim_and_close_do_not_send_queued_changes(self):
        d=self.dialog(True);self.fill(d);d.show();d.live_aim.setChecked(False)
        with patch.object(self.w.client,'request') as send:
            d.nudge('pitch_deg',2);d.flush_aim();send.assert_not_called()
            d.live_aim.setChecked(True);d.close();d.flush_aim();send.assert_not_called()

if __name__=='__main__':unittest.main()
