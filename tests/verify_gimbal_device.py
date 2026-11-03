import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from core.config import AppConfig
from core.georeference import GeoReferenceStore
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.gimbal_device import GimbalDeviceDialog


def fixture():
    sensors={key:dict(fov_deg=25,vertical_fov_deg=20,width_px=640 if key=='infrared' else 1920,height_px=512 if key=='infrared' else 1080,camera_position_cm=[0,0,100]) for key in ('visible','infrared')}
    return dict(gimbal_id='ptz-01',scene_id='city',run_id='run',yaw_deg=10,pitch_deg=5,pitch_min_deg=-15,pitch_max_deg=75,
                coordinate_pointing_supported=True,gimbal_position_cm=[0,0,0],sensors=sensors,
                devices=[dict(id='uav-01',kind='drone',position_cm=[300,400,200])])


class DeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_ranges_are_from_optical_center_not_base(self):
        w=MainWindow(AppConfig.load());d=GimbalDeviceDialog(w)
        try:
            d.update_state(fixture())
            self.assertIn('5.099 m',d.values['range'].text())
            self.assertIn('+1.000 m',d.values['range'].text())
            self.assertIn('未设置',d.values['geo'].text())
            d.disconnected();self.assertIn('不可用',d.values['range'].text());self.assertFalse(d.aim_button.isEnabled())
        finally:d.close();w.close()

    def test_simulation_anchor_and_pointing_are_explicit_and_addressed(self):
        w=MainWindow(AppConfig.load());d=GimbalDeviceDialog(w)
        try:
            with tempfile.TemporaryDirectory() as folder:
                d.store=GeoReferenceStore(folder);w.client.ready=True;d.update_state(fixture())
                self.assertIsNone(d.reference)
                d.latitude.setValue(30);d.longitude.setValue(120);d.height.setValue(100);d.save_reference()
                self.assertEqual(d.store.load('city').latitude_deg,30)
                self.assertIn('仿真',d.values['target_geo'].text())
                with patch.object(w.client,'request',return_value='point-1') as request,patch.object(w,'clear_gimbal_input'):
                    d.aim_drone();payload=request.call_args.args[1]
                    self.assertEqual(payload['device_id'],'ptz-01');self.assertEqual(payload['position_cm'],[300,400,200])
                    self.assertEqual(payload['run_id'],'run');self.assertEqual(d.pending,'point-1')
                    d.failed('unrelated','gimbal.point_at',{},'late');self.assertEqual(d.pending,'point-1')
                    d.failed('point-1','gimbal.point_at',{},'rejected');self.assertIsNone(d.pending)
        finally:w.client.ready=False;d.close();w.close()

    def test_other_gimbal_telemetry_cannot_replace_device(self):
        w=MainWindow(AppConfig.load());d=GimbalDeviceDialog(w)
        try:
            d.update_state(fixture());other=fixture();other.update(gimbal_id='ptz-02',yaw_deg=90)
            d.update_state(other);self.assertEqual(d.last['yaw_deg'],10)
        finally:d.close();w.close()


if __name__=='__main__':unittest.main()
