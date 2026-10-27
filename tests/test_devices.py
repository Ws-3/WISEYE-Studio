import copy,tempfile,unittest
from pathlib import Path
from core.devices import validate_devices,DeviceStore
from tests.test_routes import route

def devices():
    return dict(version=1,scene_id='original',devices=[dict(id='uav-01',kind='drone',name='A',model_id='mavic3',position_cm=[0,0,25],rotation_deg=[0,0,0]),dict(id='ptz-01',kind='gimbal',name='P',model_id='eo80',position_cm=[0,500,0],rotation_deg=[0,0,0],tracking_target='uav-01')])

class DeviceTests(unittest.TestCase):
    def test_roundtrip_and_reject_duplicate_unknown_target(self):
        with tempfile.TemporaryDirectory() as folder:
            store=DeviceStore(folder);store.save(devices());self.assertEqual(store.load(dict(id='original')),devices())
        for changed in ('duplicate','target','model','nan','rotation'):
            data=devices()
            if changed=='duplicate':data['devices'].append(copy.deepcopy(data['devices'][0]))
            if changed=='target':data['devices'][1]['tracking_target']='uav-99'
            if changed=='model':data['devices'][0]['model_id']='eo80'
            if changed=='nan':data['devices'][0]['position_cm'][0]=float('nan')
            if changed=='rotation':data['devices'][0]['rotation_deg'][0]=2
            with self.subTest(changed=changed),self.assertRaises(ValueError):validate_devices(data,'original')

    def test_different_instance_counts_and_independent_copies(self):
        data=devices();second=copy.deepcopy(data['devices'][0]);second['id']='uav-02';data['devices'].append(second)
        self.assertIs(validate_devices(data,'original'),data)
        data['devices'][2]['position_cm'][0]=500;self.assertEqual(data['devices'][0]['position_cm'][0],0)

class FleetControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_routes_and_inputs_are_addressed_and_unknown_ids_rejected(self):
        from unittest.mock import patch
        from tests.test_airsim_control import FakeWorld,FakeDrone
        from integrations.ProjectAirSim.run_wiseye_flight import FlightController,FleetController
        with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',return_value=None) as ue:
            first=FlightController(FakeWorld(),FakeDrone(),0,3,device_id='uav-01');second=FlightController(FakeWorld(),FakeDrone(),0,3,device_id='uav-02');fleet=FleetController([first,second])
            try:
                await fleet.execute('route.upload',dict(route(),device_id='uav-02'));self.assertIsNone(first.uploaded_route);self.assertIsNotNone(second.uploaded_route)
                await fleet.execute('flight.set_mode',dict(mode='manual',device_id='uav-02'));await fleet.execute('flight.set_input',dict(forward=1,right=0,up=0,yaw=0,device_id='uav-02'))
                self.assertEqual(first.drone.commands,[]);self.assertTrue(second.drone.commands)
                self.assertTrue(any(c.args[1].get('device_id')=='uav-02' for c in ue.call_args_list))
                with self.assertRaises(ValueError):await fleet.execute('flight.takeoff',dict(device_id='uav-99'))
                self.assertEqual(len(fleet.state()['fleet']),2)
            finally:await fleet.close()
