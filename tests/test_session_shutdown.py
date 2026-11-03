import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from apps.desktop_app.session_shutdown import land_owned_fleet


class ShutdownTests(unittest.TestCase):
    def test_never_controls_another_run(self):
        with patch('core.local_rpc.request',return_value={'payload':{'run_id':'other'}}) as rpc:
            self.assertFalse(land_owned_fleet('owned',lambda _:None))
            self.assertTrue(all(call.args[1]=='sim.get_state' for call in rpc.call_args_list))

    def test_all_drone_ids_land_and_paused_native_resumes_first(self):
        active={'run_id':'owned','fleet':[{'drone_id':i,'flight_status':'active'} for i in ('uav-01','uav-02')]}
        ready={'run_id':'owned','fleet':[{'flight_status':'ready'}]}
        responses=[{'payload':{'run_id':'owned'}},{'payload':active},{'status':'ok'},
                   {'status':'ok'},{'status':'ok'},{'status':'ok','payload':ready}]
        with patch('core.local_rpc.request',side_effect=responses) as rpc:
            self.assertTrue(land_owned_fleet('owned',lambda _:None))
            self.assertEqual(rpc.call_args_list[2].args,(50051,'sim.resume'))
            self.assertEqual([c.args[2]['device_id'] for c in rpc.call_args_list if c.args[1]=='flight.land'],['uav-01','uav-02'])

    def test_slow_land_ack_and_one_poll_timeout_still_wait_for_ready(self):
        active={'run_id':'owned','flight_status':'active','drone_id':'uav-01'}
        ready={'run_id':'owned','flight_status':'ready'}
        replies=[{'payload':{'run_id':'owned'}},{'payload':active},{'status':'ok'},
                 TimeoutError('late land ack'),TimeoutError('busy'),{'status':'ok','payload':ready}]
        with patch('core.local_rpc.request',side_effect=replies), patch('apps.desktop_app.session_shutdown.time.sleep'):
            self.assertTrue(land_owned_fleet('owned',lambda _:None))

    @unittest.skipUnless(os.name=='nt','Windows Job objects')
    def test_suspended_spawn_captures_venv_descendant_but_not_external(self):
        from core.process_job import ProcessJob
        job=ProcessJob()
        external=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            parent=job.spawn([sys.executable,'-c','import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]);time.sleep(20)'],creationflags=subprocess.CREATE_NO_WINDOW)
            deadline=time.monotonic()+5
            while len(job.pids())<3 and time.monotonic()<deadline:time.sleep(.05)
            self.assertIn(parent.pid,job.pids())
            self.assertGreaterEqual(len(job.pids()),3)
            self.assertNotIn(external.pid,job.pids())
            job.close();parent.wait(timeout=5)
            self.assertIsNone(external.poll())
        finally:
            job.close();external.terminate();external.wait(timeout=5)
