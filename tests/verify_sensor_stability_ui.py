"""Offline sensor-local projection and power-state connection regressions."""
import json
import math
import unittest
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.client import UEClient
from apps.desktop_app.lidar_view import LidarView,project_sensor_point
from core.config import AppConfig


class SensorStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_sensor_projection_has_fixed_optical_center_and_fov(self):
        self.assertEqual(project_sensor_point((10,0,0)),(0,0))
        x,y=project_sensor_point((10,10*math.tan(math.radians(15)),10*math.tan(math.radians(4))))
        self.assertAlmostEqual(x,1);self.assertAlmostEqual(y,1)
        self.assertEqual(project_sensor_point((20,2,1)),project_sensor_point((10,1,.5)))
        self.assertIsNone(project_sensor_point((-1,0,0)))
        view=LidarView();view.resize(800,500)
        try:
            self.assertEqual(view.mode.currentData(),'sensor')
            view.set_points([[10,0,0],[10,1,.2],[-1,0,0]],3,576,40,12)
            self.assertEqual((view.horizontal_fov,view.vertical_fov),(40,12))
            view.grab()
            view.mode.setCurrentIndex(view.mode.findData('3d'));view.grab()
            self.assertEqual(view.mode.currentData(),'3d')
            view.mouseDoubleClickEvent(None)
            self.assertEqual(view.mode.currentData(),'sensor')
        finally:view.close()

    def test_old_server_power_off_reply_keeps_desktop_connection_ready(self):
        from unittest.mock import patch
        fixture=dict(
            application='WISEYE Studio',paused=False,tracking=False,rotors_running=False,simulation_time_s=0,
            yaw_deg=0,pitch_deg=0,pointing_error_deg=0,fov_deg=25,flight_mode='manual',sensor_mode='visible',
            palette='white_hot',width=0,height=0,drone_position_cm=[0,0,25],sensors=dict(visible=dict(enabled=False)))
        fixture.update(width=0,height=0,sensor_mode='visible',sensors=dict(visible=dict(enabled=False)))
        client=UEClient(AppConfig());client.ready=True
        client.pending['power']=('sensor.set_enabled',0)
        client.request_payloads['power']=('sensor.set_enabled',dict(sensor='visible',enabled=False))
        packet=(json.dumps(dict(version=1,request_id='power',status='ok',payload=fixture))+'\n').encode()
        with patch.object(client.socket,'readAll',return_value=packet),patch.object(client,'disconnect_from') as disconnect:
            client._read();disconnect.assert_not_called();self.assertTrue(client.ready)
        client.disconnect_from()


if __name__=='__main__':unittest.main()
