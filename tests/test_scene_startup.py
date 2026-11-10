import asyncio,copy,unittest
from unittest.mock import patch
from integrations.ProjectAirSim.run_wiseye_flight import resolved_ue_state_ready,wait_for_ue_snapshot,ue_listener_open,restore_observer
VALID=dict(status='ok',payload=dict(scene_id='city',run_id='current-city-run',initial_drone_position_cm=[-29298.7,-100.7,25],devices=[dict(id='uav-01',kind='drone',dynamics_name='Drone1',initial_position_cm=[-29298.7,-100.7,25])]))
class SceneStartupTests(unittest.IsolatedAsyncioTestCase):
 def test_custom_scene_is_accepted_without_weakening_pose_checks(self):
  state=copy.deepcopy(VALID);state['payload']['scene_id']='laboratory_01'
  self.assertTrue(resolved_ue_state_ready(state))
  for value in ['../city','/Game/Map','CITY','',None,True]:
   state['payload']['scene_id']=value;self.assertFalse(resolved_ue_state_ready(state))
 async def test_observer_restore_requires_acknowledgement(self):
  with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',side_effect=[None,{'status':'error'},{'status':'ok'}]) as send:
   self.assertTrue(await restore_observer('overview',3))
   self.assertEqual(send.call_count,3)
   send.assert_called_with('observer.set_mode',{'mode':'overview'})
 def test_busy_listener_does_not_restart_physics(self):
  with patch('integrations.ProjectAirSim.run_wiseye_flight.socket.create_connection',side_effect=TimeoutError):self.assertTrue(ue_listener_open())
  with patch('integrations.ProjectAirSim.run_wiseye_flight.socket.create_connection',side_effect=ConnectionRefusedError):self.assertFalse(ue_listener_open())
 def test_missing_or_invalid_pose_cannot_start_physics(self):
  for reply in [None,{},dict(status='ok',payload=None),dict(status='ok',payload={})]:self.assertFalse(resolved_ue_state_ready(reply))
  for value in [None,[],[0,0,float('nan')],[True,0,0]]:
   state=copy.deepcopy(VALID);state['payload']['devices'][0]['initial_position_cm']=value;self.assertFalse(resolved_ue_state_ready(state))
  self.assertTrue(resolved_ue_state_ready(VALID))
 async def test_slow_ue_waits_for_confirmed_city_origin(self):
  with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',side_effect=[None,{},VALID]):
   result=await wait_for_ue_snapshot(2)
  self.assertEqual(result['payload']['initial_drone_position_cm'],[-29298.7,-100.7,25])
 async def test_absent_ue_times_out_instead_of_using_placeholder(self):
  with patch('integrations.ProjectAirSim.run_wiseye_flight.wiseeye_request',return_value=None):
   with self.assertRaises(TimeoutError):await wait_for_ue_snapshot(.01)
if __name__=='__main__':unittest.main()
