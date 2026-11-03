"""Physics must wait for the large city's initial collision cells to activate."""
import unittest
from integrations.ProjectAirSim.run_wiseye_flight import resolved_ue_state_ready


class LargeCityStartupTests(unittest.TestCase):
    def test_initial_cells_must_be_ready(self):
        state=dict(scene_id='city_large',run_id='run',world_streaming_enabled=True,initial_drone_position_cm=[0,0,25],
                   devices=[dict(id='uav-01',kind='drone',dynamics_name='Drone1',initial_position_cm=[0,0,25])])
        for value in (None,False,1,'true'):
            with self.subTest(value=value):
                self.assertFalse(resolved_ue_state_ready(dict(status='ok',payload=dict(state,world_streaming_ready=value))))
        self.assertTrue(resolved_ue_state_ready(dict(status='ok',payload=dict(state,world_streaming_ready=True))))
        self.assertFalse(resolved_ue_state_ready(dict(status='ok',payload=dict(state,world_streaming_ready=True,world_streaming_enabled=False))))
        self.assertTrue(resolved_ue_state_ready(dict(status='ok',payload=dict(state,scene_id='city'))))
