"""Qt regressions for per-device surface drafts; never edits the real fleet."""
import copy
import tempfile
import unittest
from unittest.mock import patch

import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from core.config import AppConfig
from core.devices import DeviceStore
from apps.desktop_app.main_window import MainWindow


class MultiPlacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.patch=patch('apps.desktop_app.arrangement.ROOT',self.temp.name);self.patch.start()
        self.store=DeviceStore(self.temp.name)
        self.window=MainWindow(AppConfig.load())
        for index in range(self.window.scenes.count()):
            if self.window.scenes.itemData(index)['id']=='city':self.window.scenes.setCurrentIndex(index);break
        self.page=self.window.arrangement;self.tools=self.page.tools
        self.fleet=self.store.load(self.window.scenes.currentData())
        extra=copy.deepcopy(self.fleet['devices'][1]);extra['id']='ptz-02';extra['name']='第二云台';extra['position_cm']=[1000,2000,80]
        self.fleet['devices'].append(extra);self.store.save(self.fleet);self.page.refresh_devices()

    def tearDown(self):
        self.window.client.ready=False;self.window.close();self.app.processEvents()
        self.patch.stop();self.temp.cleanup()

    def select(self,ident):
        key=self.page.coordinate_key(ident)
        self.tools.device.setCurrentIndex(next(i for i in range(self.tools.device.count()) if self.tools.device.itemData(i)==(ident,key)))

    def test_heading_90_loads_real_coordinates_and_enables_preview(self):
        self.fleet['devices'][0].update(rotation_deg=[0,90,0],position_cm=[-27400,-2600,4080])
        self.store.save(self.fleet);self.page.load()
        self.assertNotIn('读取失败',self.page.message.text())
        self.assertEqual(self.tools.device.count(),3)
        for actual,expected in zip(self.tools.draft()['flight_origin_cm'],[-27400,-2600,4080]):
            self.assertAlmostEqual(actual,expected,places=5)
        self.window.client.ready=True
        self.window.state=dict(scene_id='city',run_id='heading90',devices=self.fleet['devices'])
        self.tools.update_connection(self.window.state)
        self.assertTrue(self.tools.pick.isEnabled())
        self.select('uav-01')
        with patch.object(self.window,'command') as command,patch.object(self.window,'stop_manual_input'):
            self.tools.request('placement.begin')
            self.assertEqual(command.call_args.args[1]['device_id'],'uav-01')

    def test_saved_add_delete_refresh_preserves_other_position_draft(self):
        self.assertEqual(self.tools.device.count(),3)
        self.page.coordinates['ptz-02'][0].setValue(12)
        other=copy.deepcopy(self.fleet['devices'][0]);other['id']='uav-02';other['name']='第二无人机'
        self.fleet['devices'].append(other);self.store.save(self.fleet);self.page.refresh_devices()
        self.assertEqual(self.tools.device.count(),4)
        self.assertEqual(self.page.coordinates['ptz-02'][0].value(),12)
        self.select('uav-02');self.assertEqual(self.tools.clearance.value(),.25)
        self.fleet['devices'].pop();self.store.save(self.fleet);self.page.refresh_devices()
        self.assertEqual(self.tools.device.count(),3)
        self.assertNotIn('uav-02',self.page.coordinates)

    def test_surface_reply_updates_and_saves_only_the_addressed_device(self):
        original=copy.deepcopy(self.fleet['devices'][:2])
        self.select('ptz-02')
        self.window.state=dict(scene_id='city',run_id='test',devices=self.fleet['devices'])
        self.window.client.ready=True
        with patch.object(self.window,'command') as command,patch.object(self.window,'stop_manual_input'):
            self.tools.request('placement.snap')
            payload=command.call_args.args[1]
            self.assertEqual(payload['device_id'],'ptz-02')
            self.assertEqual(payload['position_cm'],[1000,2000,80])
            pending=copy.deepcopy(self.tools.pending)
            result=dict(active=False,has_result=True,device_id='ptz-01',request_token=pending['token'],position_cm=[30,40,50])
            self.tools.apply_state(dict(self.window.state,placement=result))
            self.assertIsNotNone(self.tools.pending,'Wrong device reply must not apply')
            result['device_id']='ptz-02';self.tools.apply_state(dict(self.window.state,placement=result))
        self.assertIsNone(self.tools.pending)
        self.assertEqual(self.tools.draft()['ptz-02'],[30,40,50])
        self.page.save();saved=self.store.load(self.window.scenes.currentData())
        self.assertEqual(saved['devices'][:2],original)
        self.assertEqual(saved['devices'][2]['position_cm'],[30,40,50])

    def test_unloaded_device_does_not_send_surface_request(self):
        self.select('ptz-02');self.window.client.ready=True
        self.window.state=dict(scene_id='city',run_id='test',devices=self.fleet['devices'][:2])
        with patch.object(self.window,'command') as command,patch.object(self.window,'stop_manual_input'):
            self.tools.request('placement.begin');command.assert_not_called()
        self.assertIsNone(self.tools.pending)
        self.assertIn('尚未加载',self.page.message.text())

    def test_live_coordinate_and_heading_apply_only_selected_gimbal_without_reload(self):
        self.select('ptz-02');self.window.client.ready=True
        self.window.state=dict(scene_id='city',run_id='run',devices=self.fleet['devices'],live_placement_supported=True)
        with patch.object(self.window.client,'request') as request:
            self.page.coordinates['ptz-02'][0].setValue(12.3)
            self.page.yaw_fields['ptz-02'].setValue(45)
            self.tools.apply_timer.stop();self.tools.apply_next()
            command,payload=request.call_args.args
            self.assertEqual(command,'placement.apply');self.assertEqual(payload['device_id'],'ptz-02')
            self.assertAlmostEqual(payload['position_cm'][0],1230);self.assertEqual(payload['yaw_deg'],45)
            self.tools.apply_completed(command,dict(run_id='run',placement_applied=dict(request_token=payload['request_token'],device_id='ptz-02')))
            self.assertIsNone(self.tools.apply_pending);self.assertIn('无需重载',self.page.message.text())
            self.page.save();saved=self.store.load(self.window.scenes.currentData())
            self.assertEqual(saved['devices'][2]['rotation_deg'],[0,45,0])
            self.assertEqual(saved['devices'][:2],self.fleet['devices'][:2])

    def test_live_drone_uses_physics_client_and_legacy_backend_does_not_apply(self):
        self.select('uav-01');self.window.client.ready=True;self.window.air_client.ready=True
        self.window.state=dict(scene_id='city',run_id='run',devices=self.fleet['devices'])
        with patch.object(self.window.air_client,'request') as request:
            self.tools.apply_selected();request.assert_not_called();self.assertIn('重开新版',self.page.message.text())
            self.window.state['live_placement_supported']=True;self.tools.apply_selected()
            self.assertEqual(request.call_args.args[0],'placement.apply')
            self.assertEqual(request.call_args.args[1]['device_id'],'uav-01')
            self.tools.failed('placement.apply','请先降落')
            self.assertIn('草稿保留',self.page.message.text());self.assertIsNone(self.tools.apply_pending)

    def test_confirmed_pose_keeps_yaw_and_auto_applies_without_scene_load(self):
        self.select('ptz-02');self.window.client.ready=True
        self.window.state=dict(scene_id='city',run_id='run',devices=self.fleet['devices'],live_placement_supported=True)
        with patch.object(self.window,'command'),patch.object(self.window,'stop_manual_input'),patch.object(self.window.client,'request') as request:
            self.tools.request('placement.begin');token=self.tools.pending['token']
            self.tools.apply_state(dict(self.window.state,placement=dict(has_result=True,device_id='ptz-02',request_token=token,position_cm=[10,20,30],yaw_deg=75)))
            self.tools.apply_timer.stop();self.tools.apply_next()
            self.assertEqual(request.call_args.args[1]['yaw_deg'],75)
            self.assertEqual(request.call_args.args[1]['position_cm'],[10,20,30])

    def test_run_change_and_flight_disconnect_clear_pending_application(self):
        self.window.state=dict(scene_id='city',run_id='new')
        pending=dict(scene_id='city',run_id='old',device_id='uav-01',request_token='token')
        self.tools.apply_pending=pending.copy();self.tools.apply_queue.add('flight_origin_cm')
        self.tools.apply_state(self.window.state)
        self.assertIsNone(self.tools.apply_pending);self.assertFalse(self.tools.apply_queue)
        self.tools.apply_pending=pending.copy()
        self.tools.air_connection_changed(False,'connection lost')
        self.assertIsNone(self.tools.apply_pending);self.assertIn('重连后状态',self.page.message.text())

    def test_desktop_rf_vertical_mapping_keeps_arrow_keys_out_of_drone_control(self):
        with patch.object(self.window,'send_manual_input'):
            for key,up in [(Qt.Key.Key_R,1),(Qt.Key.Key_F,-1),(Qt.Key.Key_Up,0)]:
                self.window.manual_keys={key};self.window._keyboard_manual_input()
                self.assertEqual(self.window.manual_input,(0,0,up,0))
        self.window.manual_keys.clear();self.window.manual_timer.stop()

    def test_legacy_position_preset_preserves_additional_device_and_rejects_nan(self):
        before=[v.value() for v in self.page.coordinates['ptz-02']]
        data=self.tools.draft();data.pop('ptz-02')
        data['flight_origin_cm']=[100,200,300];self.tools.set_positions(data)
        self.assertEqual([v.value() for v in self.page.coordinates['ptz-02']],before)
        from core.layouts import validate_layout
        data['ptz-02']=[0,float('nan'),0]
        with self.assertRaises(ValueError):validate_layout(data,'city')


if __name__=='__main__':unittest.main()
