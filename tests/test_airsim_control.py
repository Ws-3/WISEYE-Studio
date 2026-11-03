import asyncio
import copy
import unittest
from unittest.mock import patch

from integrations.ProjectAirSim.run_wiseye_flight import FlightController,FleetController


async def completed(value=True):
    return value


class FakeWorld:
    pass


class FakeDrone:
    def __init__(self):
        self.position = [10.0, 20.0, -5.0]
        self.commands = []
        self.cancel_count = 0
        self.orientation=dict(w=1,x=0,y=0,z=0)

    def get_ground_truth_kinematics(self):
        return {'pose': {'position': dict(zip('xyz', self.position)), 'orientation':dict(self.orientation)}}

    def get_ground_truth_pose(self):
        return dict(frame_id='DEFAULT_ID',translation=dict(zip('xyz',self.position)),rotation=dict(self.orientation))

    def set_pose(self,pose,reset_kinematics=True):
        if 'frame_id' not in pose:raise ValueError('AirSim requires frame_id')
        self.commands.append(('set_pose',copy.deepcopy(pose),reset_kinematics))
        self.position=[pose['translation'][key] for key in 'xyz'];self.orientation=dict(pose['rotation'])
        return True

    def cancel_last_task(self):
        self.cancel_count += 1
        return True

    async def hover_async(self):
        self.commands.append(('hover',))
        return asyncio.create_task(completed())

    async def move_by_velocity_body_frame_async(self, *args, **kwargs):
        self.commands.append(('manual', args, kwargs))
        return asyncio.create_task(completed())

    async def move_to_position_async(self, *args, **kwargs):
        self.commands.append(('reset', args, kwargs))
        return asyncio.create_task(completed())

    def arm(self):
        self.commands.append(('arm',))

    def disarm(self):
        self.commands.append(("disarm",))
        return True

    async def takeoff_async(self):
        self.commands.append(('takeoff',))
        return asyncio.create_task(completed())

    async def land_async(self):
        self.commands.append(('land',))
        return asyncio.create_task(completed())


class FlightControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ue_requests = patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request', return_value=None)
        self.ue_requests.start()
        self.addCleanup(self.ue_requests.stop)
        self.drone = FakeDrone()
        self.controller = FlightController(FakeWorld(), self.drone, 0, 3.0)
        self.controller.initialize_route()

    async def asyncTearDown(self):
        await self.controller.close()

    async def test_held_inputs_do_not_send_cancel_or_ue_state_sync_each_tick(self):
        ctl=self.controller;ctl.mode='manual';ctl.paused=False
        with patch.object(ctl,'ue_request') as rpc:
            fleet=FleetController([ctl])
            for i in range(100):
                state=await fleet.execute('flight.set_input',dict(forward=1))
                await asyncio.sleep(0)
            import json
            json.dumps(state)
            self.assertEqual(self.drone.cancel_count,0)
            rpc.assert_not_called()
        await ctl.execute('flight.set_input',dict(forward=0,right=0,up=0,yaw=0))
        if ctl.active_task:await ctl.active_task

    async def test_live_placement_updates_physics_home_and_heading_without_reload(self):
        ctl=self.controller;ctl.ready_on_ground=True;ctl.play_session_id='run'
        payload=dict(scene_id='city',run_id='run',request_token='token',position_cm=[1234,5678,900],yaw_deg=90)
        with patch.object(ctl,'ue_request',return_value=dict(status='ok',payload={})) as rpc:
            state=await ctl.execute('placement.apply',payload)
        self.assertEqual(self.drone.position,[12.34,56.78,-9])
        self.assertEqual(ctl.initial_position,(12.34,56.78,-9))
        self.assertAlmostEqual(state['yaw_deg'],90)
        self.assertTrue(state['placement_applied']['request_token']=='token')
        self.assertEqual([call.args[0] for call in rpc.call_args_list],['placement.validate','placement.apply'])
        self.assertTrue(self.drone.commands[-1][2]);self.assertTrue(ctl.ready_on_ground)

    async def test_live_placement_rejects_airborne_stale_and_invalid_pose(self):
        ctl=self.controller;ctl.play_session_id='run'
        valid=dict(scene_id='city',run_id='run',request_token='token',position_cm=[1,2,3],yaw_deg=0)
        with self.assertRaisesRegex(ValueError,'降落'):await ctl.execute('placement.apply',valid)
        ctl.ready_on_ground=True
        for changes in (dict(run_id='stale'),dict(position_cm=[1,float('nan'),3]),dict(yaw_deg=True)):
            with self.assertRaises(ValueError):await ctl.execute('placement.apply',dict(valid,**changes))
        self.assertFalse(any(c[0]=='set_pose' for c in self.drone.commands))

    async def test_live_placement_rolls_back_physics_and_home_when_ue_rejects(self):
        ctl=self.controller;ctl.ready_on_ground=True;ctl.play_session_id='run'
        old=self.drone.position[:];home=ctl.initial_position;path=copy.deepcopy(ctl.path)
        replies=[dict(status='ok',payload={}),dict(status='error',error=dict(message='stale session'))]
        with patch.object(ctl,'ue_request',side_effect=replies):
            with self.assertRaisesRegex(ValueError,'同步'):
                await ctl.execute('placement.apply',dict(scene_id='city',run_id='run',request_token='t',position_cm=[3,4,5],yaw_deg=90))
        self.assertEqual(self.drone.position,old);self.assertEqual(ctl.initial_position,home);self.assertEqual(ctl.path,path)
        self.assertFalse(ctl.placing)

    async def test_pause_manual_auto_and_physical_reset(self):
        state = await self.controller.execute('sim.pause', {})
        self.assertTrue(state['paused'])
        if self.controller.active_task:
            await self.controller.active_task
        self.assertEqual(self.drone.commands[-1][0], 'hover')

        state = await self.controller.execute('sim.resume', {})
        self.assertFalse(state['paused'])
        state = await self.controller.execute('flight.set_mode', {'mode': 'manual'})
        self.assertEqual(state['flight_mode'], 'manual')
        await self.controller.execute('flight.set_input', {
            'forward': 1, 'right': -.5, 'up': .25, 'yaw': .5,
        })
        command = self.drone.commands[-1]
        self.assertEqual(command[0], 'manual')
        self.assertEqual(command[1][:3], (3.0, -1.5, -0.75))

        state = await self.controller.execute('sim.reset', {})
        self.assertEqual(state['flight_mode'], 'auto')
        self.assertEqual(self.drone.commands[-1][0], 'reset')
        self.assertEqual(self.drone.commands[-1][1][:3], (10.0, 20.0, -5.0))

    async def test_rejects_invalid_manual_input(self):
        await self.controller.execute('flight.set_mode', {'mode': 'manual'})
        with self.assertRaisesRegex(ValueError, 'forward'):
            await self.controller.execute('flight.set_input', {
                'forward': 2, 'right': 0, 'up': 0, 'yaw': 0,
            })

    async def test_manual_mode_resumes_after_hover_and_release_holds_position(self):
        await self.controller.execute('flight.hover', {})
        state = await self.controller.execute('flight.set_mode', {'mode':'manual'})
        self.assertFalse(state['paused'])
        await self.controller.execute('flight.set_input', dict(forward=0,right=0,up=0,yaw=0))
        if self.controller.active_task:
            await self.controller.active_task
        self.assertEqual(self.drone.commands[-1][0], 'hover')

    async def test_paused_flight_refuses_new_motion(self):
        await self.controller.execute('flight.set_mode', {'mode':'manual'})
        await self.controller.execute('sim.pause', {})
        with self.assertRaisesRegex(ValueError,'paused'):
            await self.controller.execute('flight.set_input', dict(forward=1,right=0,up=0,yaw=0))

    async def test_old_brake_cannot_hover_over_new_motion(self):
        brake=asyncio.get_running_loop().create_future()
        async def delayed_velocity(*args, **kwargs):
            self.drone.commands.append(('manual',args,kwargs))
            return brake if not any(args[:3]) else asyncio.create_task(completed())
        self.drone.move_by_velocity_body_frame_async=delayed_velocity
        await self.controller.execute('flight.set_mode', {'mode':'manual'})
        await self.controller.execute('flight.set_input', dict(forward=1,right=0,up=0,yaw=0))
        brake.set_result(True)
        await asyncio.sleep(.02)
        self.assertFalse(any(command[0]=='hover' for command in self.drone.commands))

    async def test_takeoff_hover_and_land_controls(self):
        state = await self.controller.execute('flight.takeoff', {})
        self.assertTrue(state['paused'])
        self.assertEqual([item[0] for item in self.drone.commands[-2:]], ['arm', 'takeoff'])
        await self.controller.execute('flight.hover', {})
        if self.controller.active_task:
            await self.controller.active_task
        self.assertEqual(self.drone.commands[-1][0], 'hover')
        await self.controller.execute('flight.land', {})
        self.assertEqual(self.drone.commands[-1][0], 'land')
        await asyncio.sleep(.02)
        self.assertEqual(self.drone.commands[-1][0], 'disarm')
        self.assertTrue(self.controller.ready_on_ground)

    async def test_ready_session_never_starts_route_or_movement_before_takeoff(self):
        controller = FlightController(FakeWorld(), self.drone, 0, 3, ready_on_ground=True)
        controller.initialize_route()
        controller.start()
        try:
            await asyncio.sleep(.02)
            self.assertEqual(self.drone.commands, [])
            self.assertEqual(controller.state()['flight_status'], 'ready')
            with self.assertRaisesRegex(ValueError, 'take off'):
                await controller.execute('flight.set_mode', {'mode':'auto'})
            with self.assertRaisesRegex(ValueError, 'take off'):
                await controller.execute('flight.set_input', dict(forward=1,right=0,up=0,yaw=0))
            await controller.execute('flight.takeoff', {})
            self.assertFalse(controller.ready_on_ground)
            self.assertEqual([item[0] for item in self.drone.commands[-2:]], ['arm','takeoff'])
        finally:
            await controller.close()


if __name__ == '__main__':
    unittest.main()
