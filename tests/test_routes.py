import tempfile
import unittest
from pathlib import Path
from core.routes import validate_route,load_route,save_route

def route():
    return dict(version=1,scene_id='city',name='测试航线',frame='ue_world_m',speed_mps=2,repeat=False,waypoints=[[10,20,5],[12,20,5]])

class RouteTests(unittest.TestCase):
    def test_roundtrip_and_scene_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'route.json';save_route(path,route())
            self.assertEqual(load_route(path,'city'),route())
            with self.assertRaises(ValueError):load_route(path,'other_scene')

    def test_reject_unsafe_or_ambiguous_coordinates(self):
        for changes in [dict(waypoints=[[0,0,float('nan')],[1,0,1]]),dict(waypoints=[[0,0,1],[0,0,1]]),dict(waypoints=[[0,0,1]]),dict(speed_mps=True),dict(speed_mps=16),dict(repeat=1),dict(frame='ned'),dict(version=True)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_route(dict(route(),**changes),'city')

class ControllerRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_pause_keeps_next_unfinished_waypoint(self):
        import asyncio
        from unittest.mock import patch
        from tests.test_airsim_control import FakeWorld,FakeDrone,completed
        from integrations.ProjectAirSim.run_wiseye_flight import FlightController
        class SlowDrone(FakeDrone):
            def __init__(self):super().__init__();self.path_task=None;self.hold=False
            async def move_to_position_async(self,*args,**kwargs):
                self.commands.append(('point',args))
                if args[0]==10:return asyncio.create_task(completed())
                self.path_task=asyncio.get_running_loop().create_future()
                return self.path_task
            def cancel_last_task(self):
                if self.path_task and not self.path_task.done():self.path_task.set_result(False)
                return True
        with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',return_value=None):
            drone=SlowDrone();controller=FlightController(FakeWorld(),drone,0,3)
            try:
                await controller.execute('route.upload',route());await controller.execute('route.start',{});await asyncio.sleep(.02)
                self.assertEqual(controller.route_next_index,1)
                await controller.execute('sim.pause',{});await asyncio.sleep(.02)
                self.assertEqual(controller.route_next_index,1)
                if controller.active_task:await controller.active_task
                await controller.execute('sim.resume',{});await asyncio.sleep(.02)
                self.assertEqual([c[1][0] for c in drone.commands if c[0]=='point'],[10,12,12])
                await controller.execute('route.stop',{})
            finally:await controller.close()

    async def test_upload_is_idle_snapshot_and_start_requires_airborne(self):
        from unittest.mock import patch
        from tests.test_airsim_control import FakeWorld,FakeDrone
        from integrations.ProjectAirSim.run_wiseye_flight import FlightController
        with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',return_value=None):
            drone=FakeDrone();controller=FlightController(FakeWorld(),drone,0,3,ready_on_ground=True)
            try:
                draft=route();state=await controller.execute('route.upload',draft)
                draft['waypoints'][0][0]=999
                self.assertEqual(state['route']['waypoints'][0][0],10)
                self.assertEqual(drone.commands,[])
                with self.assertRaises(ValueError):await controller.execute('route.start',{})
                with self.assertRaises(ValueError):await controller.execute('route.upload',dict(route(),scene_id='other_scene'))
            finally:await controller.close()

    async def test_single_pass_converts_z_and_finishes_once(self):
        import asyncio
        from unittest.mock import patch
        from tests.test_airsim_control import FakeWorld,FakeDrone,completed
        from integrations.ProjectAirSim.run_wiseye_flight import FlightController
        with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',return_value=None):
            drone=FakeDrone();controller=FlightController(FakeWorld(),drone,0,3)
            try:
                await controller.execute('route.upload',route());await controller.execute('route.start',{})
                await asyncio.sleep(.1)
                self.assertEqual(controller.route_status,'completed')
                commands=[c for c in drone.commands if c[0]=='reset']
                self.assertEqual(len(commands),2);self.assertEqual([list(c[1]) for c in commands],[[10,20,-5],[12,20,-5]])
                await controller.execute('route.upload',dict(route(),name='新草稿'))
                self.assertEqual(controller.active_route['name'],'测试航线')
                await controller.execute('route.stop',{})
                self.assertEqual(controller.route_status,'stopped')
            finally:await controller.close()
