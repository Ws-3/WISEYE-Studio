import copy
import unittest
from unittest.mock import patch
from integrations.ProjectAirSim.run_wiseye_flight import ConfiguredWorld, World, FixedwingController


class FixedwingControlTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.device=dict(id='uav-01',kind='drone',model_id='fixedwing',dynamics_name='Drone1',
                         initial_position_cm=[100,200,300],position_cm=[100,200,300],
                         fixedwing=dict(active=False,paused=True,mode='auto'))
        self.snapshot=dict(run_id='run',devices=[self.device])
        self.control=FixedwingController(None,self.device,self.snapshot)
        self.control.play_session_id='run';self.control.scene_id='city'

    async def test_cruise_commands_go_to_fixedwing_not_quadrotor(self):
        calls=[]
        def request(command,payload):
            calls.append((command,payload))
            return dict(status='ok',payload=self.snapshot)
        self.control.ue_request=request
        await self.control.execute('flight.takeoff',{})
        self.assertEqual(calls[0],('flight.fixedwing',dict(action='start',run_id='run')))
        self.assertEqual(self.control.state()['motor_rpm'],[])
        self.assertEqual(self.control.state()['position_ned_m'],[1,2,-3])
        with self.assertRaises(ValueError):
            await self.control.execute('flight.land',dict(run_id='stale'))
        self.assertEqual(len(calls),1)

    async def test_route_upload_is_separate_and_requires_fixedwing_speed(self):
        route=dict(version=1,scene_id='city',name='Cruise',frame='ue_world_m',repeat=False,
                   speed_mps=2,waypoints=[[0,0,30],[100,0,30]])
        with self.assertRaises(ValueError):await self.control.execute('route.upload',route)
        route['speed_mps']=12
        await self.control.execute('route.upload',route)
        self.assertFalse(self.control.state()['command_active'])
        self.assertEqual(self.control.state()['route'],route)

    async def test_unknown_action_never_calls_ue(self):
        with self.assertRaises(KeyError):await self.control.execute('arm_quadrotor',{})


class FixedwingWorldTests(unittest.TestCase):
    def test_world_creates_physics_only_for_multirotors_in_mixed_fleet(self):
        world=object.__new__(ConfiguredWorld)
        world.initial_position_cm=None
        world.initial_devices=[dict(kind='drone',model_id='fixedwing',dynamics_name='Drone1'),
            dict(kind='drone',model_id='avata',dynamics_name='Drone2',initial_position_cm=[100,200,300])]
        config=dict(actors=[dict(name='Drone1',origin=dict(xyz='0 0 0'))])
        with patch.object(World,'load_scene',return_value=None) as load:
            world.load_scene(config)
        self.assertEqual([a['name'] for a in config['actors']],['Drone2'])
        self.assertEqual(config['actors'][0]['origin']['xyz'],'1.0 2.0 -3.0')
