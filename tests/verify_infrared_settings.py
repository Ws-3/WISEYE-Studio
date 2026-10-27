"""Qt contract for new IR controls and compatibility with old UE builds."""
import unittest
from types import SimpleNamespace
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.sensor_forms import SensorSettings
from apps.desktop_app.client import UEClient
from core.config import AppConfig


class InfraredSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_old_ue_does_not_receive_unsupported_fields(self):
        client=UEClient(AppConfig());client.ready=True
        window=SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None)
        panel=SensorSettings(window)
        try:
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':dict(enabled=True,fov_deg=25,palette='white_hot',noise=.008)}))
            self.assertNotIn('thermal_profile',panel.values('infrared'))
            self.assertFalse(panel.panels['infrared']['fields']['thermal_profile'].isEnabled())
            self.assertEqual(panel.panels['infrared']['fields']['thermal_profile'].currentData(),'legacy')
        finally:panel.close()

    def test_enhanced_parameters_are_device_scoped(self):
        client=UEClient(AppConfig());client.ready=True
        window=SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None)
        panel=SensorSettings(window)
        try:
            state=dict(enabled=True,fov_deg=25,palette='white_hot',noise=.008,thermal_profile='enhanced',
                       enhanced_available=True,blur_px=.8,contrast=1.35,background_detail=.65)
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':state}))
            self.assertTrue(panel.panels['infrared']['fields']['thermal_profile'].isEnabled())
            self.assertEqual(panel.values('infrared')['blur_px'],.8)
            panel.panels['infrared']['fields']['blur_px'].setValue(1.2)
            self.assertEqual(panel.bank[('ptz-01','infrared')]['values']['blur_px'],1.2)
            self.assertEqual(panel.panels['infrared']['confirmed']['blur_px'],.8)
            panel.update_state(dict(gimbal_id='ptz-02',sensors={'infrared':dict(state,blur_px=.3,thermal_profile='legacy')}))
            panel.select_device('ptz-02')
            self.assertEqual(panel.values('infrared')['blur_px'],.3)
            panel.select_device('ptz-01')
            self.assertEqual(panel.values('infrared')['blur_px'],1.2)
        finally:panel.close()


if __name__=='__main__':unittest.main()
