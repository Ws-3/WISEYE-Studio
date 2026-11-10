import unittest
from integrations.ProjectAirSim.live_fleet import LiveFleetMixin


class TeleportTests(unittest.IsolatedAsyncioTestCase):
    async def test_collision_lease_is_restored_if_sdk_pose_fails(self):
        class Service(LiveFleetMixin):
            run_id='current-run'
            def __init__(self):self.commands=[]
            async def _native(self,command,payload):self.commands.append((command,dict(payload)));return {}
        class Robot:
            name='Drone2'
            def set_pose(self,pose,reset):raise OSError('Disconnected')
        service=Service()
        with self.assertRaises(OSError):await service._write_pose(Robot(),{})
        self.assertEqual([c for c,p in service.commands],['flight.prepare_slot','flight.finish_slot'])
        self.assertEqual(service.commands[0][1],service.commands[1][1])
        self.assertEqual(service.commands[0][1]['run_id'],'current-run')

    async def test_slot_lease_released_after_successful_pose(self):
        class Service(LiveFleetMixin):
            run_id='run'
            def __init__(self):self.commands=[]
            async def _native(self,command,payload):self.commands.append(command);return {}
        class Robot:
            name='Drone3'
            def set_pose(self,pose,reset):return True
        service=Service();await service._write_pose(Robot(),{})
        self.assertEqual(service.commands,['flight.prepare_slot','flight.finish_slot'])
