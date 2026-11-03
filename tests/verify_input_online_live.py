"""60-second real manual stream on an explicitly owned, isolated UE run."""
import argparse
from collections import deque
import json
from pathlib import Path
import statistics
import time
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from core.config import AppConfig
from apps.desktop_app.airsim_client import AirSimClient
from training_client.client import Client


def main():
    p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    owned=json.loads(args.ready.read_text());ue=Client(port=50051);rpc=Client(port=50052,device='uav-01')
    assert ue.rpc('sim.get_state')['run_id']==owned['run_id']
    app=QApplication.instance() or QApplication([]);client=AirSimClient(AppConfig())
    report=dict(passed=False,run_id=owned['run_id']);airborne=False;requests=deque();samples=[];errors=[]
    original_request=client.request
    def send(command,payload=None):
        existing=set(client.pending);started=time.monotonic();request_id=original_request(command,payload)
        if command=='flight.set_input' and request_id and request_id not in existing:
            requests.append((request_id,started,dict(payload or {})))
        return request_id
    client.request=send
    def complete(command,state):
        if command=='flight.set_input':
            _,started,payload=requests.popleft();samples.append(dict(at=started,delay=time.monotonic()-started,values=payload))
    client.completed.connect(complete);client.failed.connect(lambda command,error:errors.append((command,error)))
    def wait(predicate,limit=70):
        until=time.monotonic()+limit
        while time.monotonic()<until:
            app.processEvents()
            if predicate():return
            time.sleep(.005)
        raise TimeoutError(str(errors[-3:]))
    try:
        rpc.rpc('flight.takeoff');airborne=True
        wait(lambda:not rpc.rpc('sim.get_state')['command_active'])
        rpc.rpc('flight.set_mode',mode='manual');wait(lambda:not rpc.rpc('sim.get_state')['command_active'])
        client.connect_to();wait(lambda:client.ready)
        start=time.monotonic();next_send=start;maximum_pending=0
        print('HOLD_STARTED',flush=True)
        while time.monotonic()-start<60:
            now=time.monotonic();app.processEvents()
            if now>=next_send:
                client.request('flight.set_input',dict(forward=0,right=0,up=0,yaw=.25));next_send=now+.12
            maximum_pending=max(maximum_pending,len(client.input_requests))
            assert not errors,errors
            time.sleep(.005)
        released=time.monotonic();client.request('flight.set_input',dict(forward=0,right=0,up=0,yaw=0))
        wait(lambda:any(s['at']>=released and not any(s['values'].get(k,0) for k in ('forward','right','up','yaw')) for s in samples),4)
        report['release_ack_ms']=1000*(time.monotonic()-released)
        early=[s['delay'] for s in samples if s['at']<start+10]
        late=[s['delay'] for s in samples if s['at']>start+50]
        report.update(ack_count=len(samples),first_10s_median_ms=1000*statistics.median(early),last_10s_median_ms=1000*statistics.median(late),max_pending_per_drone=maximum_pending)
        assert maximum_pending<=1 and report['last_10s_median_ms']<500 and report['release_ack_ms']<1000,report
        print('HOLD_AND_RELEASE_PASSED',flush=True)
        rpc.rpc('flight.land');wait(lambda:rpc.rpc('sim.get_state')['flight_status']=='ready' and max(rpc.rpc('sim.get_state')['motor_rpm'])<1)
        airborne=False;report['passed']=True;report['final']=rpc.rpc('sim.get_state')
    finally:
        client.disconnect_from()
        if airborne:
            rpc.rpc('flight.land');wait(lambda:rpc.rpc('sim.get_state')['flight_status']=='ready' and max(rpc.rpc('sim.get_state')['motor_rpm'])<1)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='final'},indent=2),flush=True)


if __name__=='__main__':main()
