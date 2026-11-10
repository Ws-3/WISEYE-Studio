import unittest
from types import SimpleNamespace
from unittest.mock import patch
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.sensor_forms import SensorSettings
from apps.desktop_app.sensor_power import SensorPowerPanel
from apps.desktop_app.client import UEClient
from apps.desktop_app.source_registry import Source,DEFAULT_SOURCES
from core.config import AppConfig


class EventSensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_independent_controls_and_addressed_parameters(self):
        client=UEClient(AppConfig());client.ready=True
        settings=SensorSettings(SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None))
        power=SensorPowerPanel(settings)
        try:
            event=dict(enabled=False,fov_deg=25,sample_hz=30,positive_threshold=.2,negative_threshold=.2,refractory_us=100,extrinsics_supported=True,mount_x_cm=0,mount_y_cm=0,mount_z_cm=2,boresight_pitch_deg=0,boresight_yaw_deg=0,boresight_roll_deg=0)
            settings.update_state(dict(run_id='run',gimbal_id='ptz-01',sensor_power_supported=True,sensors=dict(event=event)))
            self.assertEqual(settings.count(),4);self.assertIn('事件',settings.tabText(3))
            self.assertFalse(settings.values('event')['enabled'])
            settings.panels['event']['fields']['positive_threshold'].setValue(.3)
            with patch.object(client,'request',return_value='enable') as call:
                settings.submit_power('event')
                self.assertEqual(call.call_args.args,('sensor.set_enabled',dict(device_id='ptz-01',sensor='event',enabled=True)))
            settings.select_device('ptz-02')
            self.assertEqual(settings.panels['event']['fields']['mount_z_cm'].value(),2)
            self.assertTrue(settings.values('event')['enabled'])
        finally:power.close();settings.close()
    def test_default_event_preview_is_independent_not_rtsp(self):
        self.assertEqual(Source.parse('ptz-01/event').url('127.0.0.1',AppConfig()),'')
        self.assertIn('ptz-01/event',DEFAULT_SOURCES)
    def test_visible_response_requires_capability_and_is_device_addressed(self):
        client=UEClient(AppConfig());client.ready=True
        settings=SensorSettings(SimpleNamespace(selected_gimbal='ptz-01',client=client,capture_source=lambda *a:None))
        try:
            neutral=dict(enabled=True,fov_deg=25,appearance_available=True,blur_px=.55,noise=.006,contrast=.96,saturation=.88)
            settings.update_state(dict(run_id='run',gimbal_id='ptz-01',sensor_power_supported=True,sensors=dict(visible=neutral)))
            settings.panels['visible']['fields']['blur_px'].setValue(1.2)
            with patch.object(client,'request',return_value='visible-request') as call:
                settings.submit('visible')
                self.assertEqual(call.call_args.args[0],'sensor.configure')
                payload=call.call_args.args[1]
                self.assertEqual(payload['device_id'],'ptz-01');self.assertEqual(payload['blur_px'],1.2)
                self.assertEqual(payload['saturation'],.88)
            settings.select_device('ptz-02')
            self.assertNotIn('blur_px',settings.values('visible'))
        finally:settings.close()
    def test_worker_can_finish_after_qobject_destruction(self):
        from apps.desktop_app.event_preview_client import EventPreviewClient
        import shiboken6
        client=EventPreviewClient();client.running=True;client._generation=1
        shiboken6.delete(client)
        with patch('apps.desktop_app.event_preview_client.request',return_value=dict(status='error',error=dict(message='disabled'))):
            client._worker(1,('127.0.0.1',50051,'ptz-01'))
    def test_worker_does_not_signal_after_stop_during_rpc(self):
        from apps.desktop_app.event_preview_client import EventPreviewClient
        client=EventPreviewClient();client.running=True;client._generation=1
        def stopped(*a,**kw):client.stop();raise OSError('closed')
        with patch('apps.desktop_app.event_preview_client.request',side_effect=stopped):
            client._worker(1,('127.0.0.1',50051,'ptz-01'))
        client.deleteLater()


if __name__=='__main__':unittest.main()
