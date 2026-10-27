import math
import unittest
from unittest.mock import patch
from core.simulation_health import SimulationHealth
from integrations.gimbal_client import GimbalClient
from integrations.ProjectAirSim.run_wiseye_flight import FlightController


class RuntimeHealthTests(unittest.TestCase):
    def test_live_connection_with_frozen_sequence_is_unhealthy(self):
        health=SimulationHealth()
        health.observe(dict(run_id='a',tick_seq=10),0)
        health.observe(dict(run_id='a',tick_seq=10),4)
        self.assertFalse(health.status(4,True)[0])
        health.observe(dict(run_id='a',tick_seq=11),4.1)
        self.assertTrue(health.status(4.1,True)[0])
        self.assertFalse(health.status(8,True)[0])

    def test_render_stall_and_new_session(self):
        health=SimulationHealth()
        state=dict(run_id='a',tick_seq=1,sensors=dict(visible=dict(enabled=True)),
                   streams=dict(CH1=dict(cache_age_ms=5000)))
        health.observe(state,10)
        self.assertIn('渲染',health.status(10,True)[1])
        health.observe(dict(run_id='b',tick_seq=1),12)
        self.assertTrue(health.status(12,True)[0])
        self.assertFalse(health.status(12,False)[0])

    def test_motor_conversion_reordering_and_stale_native_timestamp(self):
        ctl=FlightController(None,None,0,1)
        motors=['Prop_RR_actuator','Prop_FL_actuator','Prop_RL_actuator','Prop_FR_actuator']
        sample=dict(time_stamp=10,rotor_info_vec=[dict(rotor_id=k,speed=v*math.pi/30)
                                               for k,v in zip(motors,[4000,1000,3000,2000])])
        with patch('integrations.ProjectAirSim.run_wiseye_flight.time.monotonic',return_value=1):ctl.on_rotors('',sample)
        self.assertEqual(tuple(round(v) for v in ctl.rotor_sample[2]),(1000,2000,3000,4000))
        previous=ctl.rotor_sample
        ctl.on_rotors('',sample)
        self.assertEqual(previous,ctl.rotor_sample)
        sample['time_stamp']=11;sample['rotor_info_vec'][0]['speed']=float('nan')
        ctl.on_rotors('',sample)
        self.assertEqual(previous,ctl.rotor_sample)

    def test_gimbal_sdk_velocity_is_explicit_and_bounded(self):
        gimbal=GimbalClient('ptz-02')
        with patch.object(gimbal,'request') as request:
            gimbal.set_velocity(15,-10)
            request.assert_called_once_with('gimbal.set_input',yaw=.5,pitch=-.5)
            for bad in (31,float('nan'),True):
                with self.assertRaises(ValueError):gimbal.set_velocity(bad)
