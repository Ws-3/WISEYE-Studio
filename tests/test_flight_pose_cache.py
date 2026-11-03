import math
import asyncio
import unittest
from unittest.mock import patch
from integrations.ProjectAirSim.run_wiseye_flight import FlightController,FleetController,handle_control,close_control_server
from tests.test_airsim_control import FakeWorld,FakeDrone


def pose(stamp=10):
    return dict(time_stamp=stamp,position=dict(x=12,y=20,z=-7),orientation=dict(w=math.sqrt(.5),x=0,y=0,z=math.sqrt(.5)))


class PoseCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_closes_idle_persistent_client_before_waiting(self):
        ctl=FlightController(FakeWorld(),FakeDrone(),0,3)
        fleet=FleetController([ctl])
        server=await asyncio.start_server(lambda r,w:handle_control(r,w,fleet),'127.0.0.1',0)
        reader,writer=await asyncio.open_connection('127.0.0.1',server.sockets[0].getsockname()[1])
        try:
            for _ in range(20):
                if fleet.control_writers:break
                await asyncio.sleep(.01)
            self.assertTrue(fleet.control_writers)
            with patch.object(ctl,'_cancel_active',side_effect=AssertionError('retired physics RPC')):
                await asyncio.wait_for(close_control_server(server,fleet,skip_remote=True),1)
            self.assertEqual(await asyncio.wait_for(reader.read(),1),b'')
            self.assertTrue(ctl.closed)
            self.assertFalse(server.is_serving())
        finally:
            writer.close();await writer.wait_closed()
            server.close();await server.wait_closed()

    async def test_state_and_fleet_queries_never_call_physics_rpc(self):
        drone=FakeDrone();ctl=FlightController(FakeWorld(),drone,0,3);ctl.initialize_route()
        ctl.on_pose('',pose());fleet=FleetController([ctl])
        with patch.object(drone,'get_ground_truth_kinematics',side_effect=AssertionError('retired world RPC')),patch.object(ctl,'ue_request',side_effect=AssertionError('extra UE poll')):
            state=await fleet.execute('sim.get_state',{})
            self.assertEqual(state['position_ned_m'],[12.,20.,-7.])
            self.assertAlmostEqual(state['yaw_deg'],90)
            self.assertTrue(state['telemetry_valid'])
            self.assertEqual(state['telemetry_source'],'actual_pose_topic')

    async def test_stale_pose_retains_position_and_marks_disconnected(self):
        ctl=FlightController(FakeWorld(),FakeDrone(),0,3);ctl.on_pose('',pose())
        t=ctl.pose_sample[0]
        with patch('integrations.ProjectAirSim.run_wiseye_flight.time.monotonic',return_value=t+3):
            s=ctl.state();self.assertFalse(s['connected']);self.assertFalse(s['telemetry_valid'])
            self.assertEqual(s['position_ned_m'],[12.,20.,-7.]);self.assertEqual(s['telemetry_age_s'],3)

    async def test_invalid_duplicate_and_out_of_order_samples_are_ignored(self):
        ctl=FlightController(FakeWorld(),FakeDrone(),0,3);ctl.on_pose('',pose());original=ctl.pose_sample
        cases=[pose(10),pose(9),pose(True),{},dict(pose(11),position=dict(x=float('nan'),y=0,z=0)),
               dict(pose(11),orientation=dict(w=0,x=0,y=0,z=0))]
        for invalid in cases:
            ctl.on_pose('',invalid);self.assertEqual(ctl.pose_sample,original)
        ctl.on_pose('',pose(11));self.assertEqual(ctl.pose_sample[1],11)
