import asyncio
import unittest

from integrations.ProjectAirSim.run_wiseye_flight import FlightController


async def completed(value=True):
    return value


class FakeWorld:
    pass


class FakeDrone:
    def __init__(self):
        self.position = [10.0, 20.0, -5.0]
        self.commands = []
        self.cancel_count = 0

    def get_ground_truth_kinematics(self):
        return {'pose': {'position': dict(zip('xyz', self.position))}}

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

    async def takeoff_async(self):
        self.commands.append(('takeoff',))
        return asyncio.create_task(completed())

    async def land_async(self):
        self.commands.append(('land',))
        return asyncio.create_task(completed())


class FlightControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.drone = FakeDrone()
        self.controller = FlightController(FakeWorld(), self.drone, 0, 3.0)
        self.controller.initialize_route()

    async def asyncTearDown(self):
        await self.controller.close()

    async def test_pause_manual_auto_and_physical_reset(self):
        state = await self.controller.execute('sim.pause', {})
        self.assertTrue(state['paused'])
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

    async def test_takeoff_hover_and_land_controls(self):
        state = await self.controller.execute('flight.takeoff', {})
        self.assertTrue(state['paused'])
        self.assertEqual([item[0] for item in self.drone.commands[-2:]], ['arm', 'takeoff'])
        await self.controller.execute('flight.hover', {})
        self.assertEqual(self.drone.commands[-1][0], 'hover')
        await self.controller.execute('flight.land', {})
        self.assertEqual(self.drone.commands[-1][0], 'land')


if __name__ == '__main__':
    unittest.main()
