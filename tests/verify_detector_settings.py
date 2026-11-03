import unittest
from unittest.mock import patch
from types import SimpleNamespace
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.sensor_forms import SensorSettings
from apps.desktop_app.client import UEClient
from core.config import AppConfig
from core.infrared_presets import DETECTOR_FIELDS


class DetectorSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.client=UEClient(AppConfig());self.client.ready=True
        self.panel=SensorSettings(SimpleNamespace(selected_gimbal='ptz-01',client=self.client,capture_source=lambda *a:None))
        self.actual=dict(enabled=True,fov_deg=45,palette='white_hot',noise=0,thermal_profile='facade',enhanced_available=True,
            reference_available=True,classified_available=True,facade_available=True,detector_controls_available=True,
            blur_px=.8,contrast=1.1,background_detail=.6,agc_enabled=True,agc_response_s=1,sampling_scale=1,
            gain_mode='auto',stable_agc=False,manual_low=0,manual_high=1,brightness=0,sky_denoise=0,noise_seed=1337)
        self.panel.update_state(dict(gimbal_id='ptz-01',sensors=dict(infrared=self.actual)))
    def tearDown(self):self.panel.close()
    def test_only_current_model_and_no_presets_are_exposed(self):
        fields=self.panel.panels['infrared']['fields']
        self.assertTrue(fields['thermal_profile'].isHidden())
        self.assertEqual(fields['thermal_profile'].count(),1)
        self.assertFalse(hasattr(self.panel,'preset_buttons'))

    def test_mode_controls_and_legacy_agc_are_consistent(self):
        f=self.panel.panels['infrared']['fields']
        self.assertFalse(f['manual_low'].isEnabled());self.assertFalse(f['agc_enabled'].isEnabled())
        f['gain_mode'].setCurrentIndex(f['gain_mode'].findData('manual'))
        self.assertTrue(f['manual_low'].isEnabled());self.assertFalse(self.panel.values('infrared')['agc_enabled'])
        f['gain_mode'].setCurrentIndex(f['gain_mode'].findData('locked'))
        self.assertFalse(f['manual_low'].isEnabled());self.assertFalse(f['stable_agc'].isEnabled())
    def test_parameter_edits_are_drafts_and_preserve_fov(self):
        with patch.object(self.client,'request') as request:
            self.panel.panels['infrared']['fields']['sky_denoise'].setValue(.8);self.panel.panels['infrared']['fields']['stable_agc'].setChecked(True);request.assert_not_called()
        values=self.panel.values('infrared');self.assertEqual(values['fov_deg'],45)
        self.assertEqual(values['sky_denoise'],.8);self.assertTrue(values['stable_agc'])
        self.assertTrue(self.panel.panels['infrared']['dirty'])
    def test_inverted_range_is_explained_before_sending(self):
        f=self.panel.panels['infrared']['fields'];f['manual_low'].setValue(.6);f['manual_high'].setValue(.4)
        with patch.object(self.client,'request') as request:
            self.panel.submit('infrared');request.assert_not_called()
        self.assertIn('0.01',self.panel.panels['infrared']['status'].text())
    def test_detector_drafts_are_per_device_and_old_ue_gets_no_new_fields(self):
        self.panel.panels['infrared']['fields']['sky_denoise'].setValue(.8);self.panel.panels['infrared']['fields']['stable_agc'].setChecked(True)
        self.panel.update_state(dict(gimbal_id='ptz-02',sensors=dict(infrared=dict(self.actual,detector_controls_available=False))))
        self.panel.select_device('ptz-02')
        self.assertFalse(any(k in self.panel.values('infrared') for k in DETECTOR_FIELDS))
        self.panel.select_device('ptz-01');self.assertEqual(self.panel.values('infrared')['sky_denoise'],.8)
        self.assertTrue(self.panel.panels['infrared']['dirty'])
    def test_extrinsics_are_independent_of_picture_parameters(self):
        data=dict(self.actual,extrinsics_supported=True,mount_x_cm=0,mount_y_cm=6,mount_z_cm=0,
            boresight_pitch_deg=.1,boresight_yaw_deg=.2,boresight_roll_deg=0)
        self.panel.update_state(dict(gimbal_id='ptz-01',sensors=dict(infrared=data)))
        fields=self.panel.panels['infrared']['fields'];fields['mount_y_cm'].setValue(8)
        self.panel.panels['infrared']['fields']['noise'].setValue(.002)
        self.assertEqual(self.panel.values('infrared')['mount_y_cm'],8)
        self.assertEqual(self.panel.values('infrared')['boresight_yaw_deg'],.2)
        self.assertFalse('mount_y_cm' in self.panel.values('visible'))
    def test_old_backend_disables_and_omits_extrinsics(self):
        self.assertFalse(self.panel.panels['infrared']['fields']['mount_y_cm'].isEnabled())
        self.assertFalse('mount_y_cm' in self.panel.values('infrared'))


if __name__=='__main__':unittest.main()
