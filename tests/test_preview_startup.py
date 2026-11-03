"""Supervisor readiness must match the new UE run before automatic connect."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch
from apps.desktop_app.preview_session import run


class PreviewStartupTests(unittest.TestCase):
    def exercise(self,failed=False):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder);(data/'logs').mkdir()
            config=data/'ue5/WISEYE/Config/WISEYE/Scenes';config.mkdir(parents=True)
            (config/'city.json').write_text(json.dumps(dict(map='/city')))
            processes=[];stages=[];tick=[0];status_path=[None];polls=[0]
            def spawn(command,**kwargs):
                p=MagicMock();p.pid=100+len(processes);p.poll.return_value=None
                p.wait.side_effect=lambda **_:setattr(p.poll,'return_value',0)
                processes.append(p)
                status_path[0]=Path(kwargs['env']['WISEYE_SESSION_STATUS'])
                stages.append(json.loads(status_path[0].read_text())['stage'])
                return p
            def sleep(_):
                tick[0]+=1;stages.append(json.loads(status_path[0].read_text())['stage'])
                if failed and tick[0]==1:processes[1].poll.return_value=1
                if tick[0]==3:processes[2].poll.return_value=0
            def rpc(port,*_):
                if port==50051:return dict(payload=dict(scene_id='city',run_id='new',devices=[1],initial_drone_position_cm=[1,2,3]))
                polls[0]+=1
                return dict(payload=dict(run_id='old' if polls[0]==1 else 'new',flight_status='ready'))
            job=MagicMock();job.spawn.side_effect=spawn;job.pids.return_value={100,101,102}
            with patch('apps.desktop_app.preview_session.ProcessJob',return_value=job),patch('apps.desktop_app.preview_session.request',side_effect=rpc),patch('apps.desktop_app.preview_session.time.sleep',side_effect=sleep),patch('apps.desktop_app.preview_session.close_windows'),patch('apps.desktop_app.preview_session.land_owned_fleet'):
                run(argparse.Namespace(data=str(data),scene='city',editor='fake',project='fake'))
            job.close.assert_called_once()
            self.assertEqual(stages[:3],['loading']*3)
            self.assertEqual(stages[3:5],['flight','failed'] if failed else ['flight','flight'])
            self.assertEqual(stages[-1],'failed' if failed else 'ready')

    def test_waits_for_matching_run(self):self.exercise()
    def test_failed_worker_leaves_failure_visible_until_desktop_closes(self):self.exercise(True)
