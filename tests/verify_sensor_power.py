import unittest
from types import SimpleNamespace
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.sensor_forms import SensorSettings
from apps.desktop_app.sensor_power import SensorPowerPanel
from apps.desktop_app.client import UEClient
from core.config import AppConfig


class SensorPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.client=UEClient(AppConfig());self.client.ready=True
        self.settings=SensorSettings(SimpleNamespace(selected_gimbal='ptz-01',client=self.client,capture_source=lambda *a:None))
        self.power=SensorPowerPanel(self.settings)
        self.sensor=dict(enabled=True,fov_deg=25,palette='white_hot',noise=.008,thermal_profile='facade',
            enhanced_available=True,reference_available=True,classified_available=True,facade_available=True,
            blur_px=.8,contrast=1.15,background_detail=.8,agc_enabled=True,agc_response_s=.4,sampling_scale=1)
        self.state=dict(run_id='one',gimbal_id='ptz-01',sensor_power_supported=True,sensors=dict(infrared=self.sensor))
        self.settings.update_state(self.state)

    def tearDown(self):self.power.close();self.settings.close()

    def test_power_does_not_submit_or_discard_parameter_drafts(self):
        s=self.settings;s.panels['infrared']['fields']['blur_px'].setValue(1.2)
        with patch.object(self.client,'request',return_value='power') as request:
            s.submit_power('infrared')
            self.assertEqual(request.call_args.args,('sensor.set_enabled',dict(device_id='ptz-01',sensor='infrared',enabled=False)))
        self.assertFalse(self.power.buttons['infrared'][0].isEnabled())
        actual=dict(self.state,sensors=dict(infrared=dict(self.sensor,enabled=False)))
        s.update_state(actual);s.acknowledged('unrelated','sensor.set_enabled',{},actual)
        self.assertIn('power',s.pending)
        s.acknowledged('power','sensor.set_enabled',{},actual)
        self.assertEqual(s.values('infrared')['blur_px'],1.2)
        self.assertFalse(s.values('infrared')['enabled']);self.assertTrue(s.panels['infrared']['dirty'])
        self.assertIn('开启',self.power.buttons['infrared'][0].text())

    def test_late_ack_updates_only_the_addressed_device(self):
        s=self.settings
        with patch.object(self.client,'request',return_value='power'):s.submit_power('infrared')
        s.update_state(dict(self.state,gimbal_id='ptz-02'));s.select_device('ptz-02')
        actual=dict(self.state,sensors=dict(infrared=dict(self.sensor,enabled=False)))
        s.update_state(actual);s.acknowledged('power','sensor.set_enabled',{},actual)
        self.assertTrue(s.values('infrared')['enabled'])
        s.select_device('ptz-01');self.assertFalse(s.values('infrared')['enabled'])

    def test_older_ue_and_disconnect_do_not_offer_live_switches(self):
        self.settings.update_state(dict(self.state,sensor_power_supported=False))
        self.assertFalse(self.power.buttons['infrared'][0].isEnabled())
        self.settings.disconnected();self.assertFalse(self.power.buttons['infrared'][0].isEnabled())

    def test_failure_does_not_pretend_sensor_stopped(self):
        with patch.object(self.client,'request',return_value='power'):self.settings.submit_power('infrared')
        self.settings.rejected('power','sensor.set_enabled',{},'rejected')
        self.assertTrue(self.settings.panels['infrared']['confirmed']['enabled'])
        self.assertIn('停止',self.power.buttons['infrared'][0].text())


if __name__=='__main__':unittest.main()
