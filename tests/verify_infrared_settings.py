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
            self.assertEqual(panel.panels['infrared']['fields']['thermal_profile'].currentData(),'facade')
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

    def test_reference_controls_follow_capability_and_keep_device_drafts(self):
        client=UEClient(AppConfig());client.ready=True
        window=SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None)
        panel=SensorSettings(window)
        try:
            state=dict(enabled=True,fov_deg=25,palette='white_hot',noise=.008,thermal_profile='facade',
                       enhanced_available=True,reference_available=True,blur_px=.8,contrast=1.35,background_detail=.65,
                       agc_enabled=True,agc_response_s=1,sampling_scale=1)
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':state}))
            fields=panel.panels['infrared']['fields']
            self.assertTrue(fields['agc_enabled'].isEnabled())
            fields['agc_response_s'].setValue(2.3)
            panel.update_state(dict(gimbal_id='ptz-02',sensors={'infrared':dict(state,agc_response_s=.4)}))
            panel.select_device('ptz-02');self.assertEqual(panel.values('infrared')['agc_response_s'],.4)
            panel.select_device('ptz-01');self.assertEqual(panel.values('infrared')['agc_response_s'],2.3)
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':dict(state,reference_available=False,thermal_profile='enhanced')}))
            self.assertNotIn('agc_response_s',panel.values('infrared'))
            self.assertFalse(fields['agc_enabled'].isEnabled())
        finally:panel.close()


    def test_facade_is_disabled_on_older_materials_and_keeps_device_drafts(self):
        client=UEClient(AppConfig());client.ready=True
        window=SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None)
        panel=SensorSettings(window)
        try:
            state=dict(enabled=True,fov_deg=25,palette='white_hot',noise=.008,thermal_profile='facade',
                       enhanced_available=True,reference_available=True,classified_available=True,facade_available=True,
                       agc_enabled=True,agc_response_s=1,sampling_scale=1,background_detail=.65)
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':state}))
            fields=panel.panels['infrared']['fields']
            self.assertTrue(fields['agc_enabled'].isEnabled())
            self.assertIn('红外',panel.panels['infrared']['actual'].text())
            fields['background_detail'].setValue(.8)
            panel.update_state(dict(gimbal_id='ptz-02',sensors={'infrared':dict(state,facade_available=False,thermal_profile='reference')}))
            panel.select_device('ptz-02')
            self.assertFalse(fields['thermal_profile'].model().item(fields['thermal_profile'].findData('facade')).isEnabled())
            panel.select_device('ptz-01')
            self.assertEqual(panel.values('infrared')['thermal_profile'],'facade')
            self.assertEqual(panel.values('infrared')['background_detail'],.8)
        finally:panel.close()

    def test_material_mode_requires_capability_and_reports_pixel_coverage(self):
        client=UEClient(AppConfig());client.ready=True
        window=SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None)
        panel=SensorSettings(window)
        try:
            state=dict(enabled=True,fov_deg=25,palette='white_hot',noise=.008,thermal_profile='facade',facade_available=True,
                       enhanced_available=True,reference_available=True,classified_available=True,
                       agc_enabled=True,agc_response_s=1,sampling_scale=1,class_pixels=[75,25,0,0,0,0,0])
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':state}))
            fields=panel.panels['infrared']['fields']
            self.assertTrue(fields['agc_enabled'].isEnabled())
            self.assertIn('25%',panel.panels['infrared']['actual'].text())
            self.assertIn('已确认',panel.panels['infrared']['status'].text())
            panel.update_state(dict(gimbal_id='ptz-01',sensors={'infrared':dict(state,classified_available=False,thermal_profile='reference')}))
            self.assertEqual(fields['thermal_profile'].findData('classified'),-1)
        finally:panel.close()


if __name__=='__main__':unittest.main()
