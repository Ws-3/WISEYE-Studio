"""Only run against an explicitly owned test session; restores every pose."""
import argparse
import json
import math
from pathlib import Path
import time
import uuid
from training_client.client import Client,RPCError


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--owned-run',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    ue=Client(port=50051);air=Client(port=50052,device='uav-01')
    state=ue.rpc('sim.get_state');assert state['run_id']==args.owned_run and state['live_placement_supported']
    report=dict(passed=False,run_id=state['run_id']);original={d['id']:d for d in state['devices']}
    def wait(predicate,limit=75):
        until=time.monotonic()+limit
        while time.monotonic()<until:
            if predicate():return
            time.sleep(.15)
        raise TimeoutError('Live placement/flight check timed out')
    def apply(ident,xyz,yaw):
        payload=dict(scene_id='city',run_id=args.owned_run,request_token=uuid.uuid4().hex,position_cm=xyz,yaw_deg=yaw)
        client=Client(port=50052 if ident.startswith('uav-') else 50051,device=ident)
        result=client.rpc('placement.apply',**payload)
        assert result['placement_applied']['request_token']==payload['request_token']
        assert result['run_id']==args.owned_run
        return result
    def device(ident):return next(d for d in ue.rpc('sim.get_state')['devices'] if d['id']==ident)
    airborne=False
    try:
        gimbal=original['ptz-01'];position=[gimbal['position_cm'][0]+20,gimbal['position_cm'][1]+10,gimbal['position_cm'][2]]
        yaw=(gimbal['placement_yaw_deg']+15+180)%360-180
        apply('ptz-01',position,yaw);time.sleep(.5)
        actual=device('ptz-01');assert math.dist(actual['position_cm'],position)<.1
        assert abs(actual['placement_yaw_deg']-yaw)<.01
        report['gimbal']=dict(requested=position,actual=actual['position_cm'],yaw=yaw)
        apply('ptz-01',gimbal['position_cm'],gimbal['placement_yaw_deg'])
        drone=original['uav-01'];position=[drone['position_cm'][0]+50,drone['position_cm'][1]+30,drone['position_cm'][2]]
        yaw=(drone['placement_yaw_deg']+30+180)%360-180
        before=air.rpc('sim.get_state');assert before['flight_status']=='ready' and max(before['motor_rpm'])<1
        apply('uav-01',position,yaw);time.sleep(2)
        actual=device('uav-01');assert math.dist(actual['position_cm'][:2],position[:2])<2
        assert math.dist(actual['initial_position_cm'],position)<.1
        report['drone']=dict(requested=position,actual_after_2s=actual['position_cm'],physics=air.rpc('sim.get_state'))
        try:
            ue.rpc('placement.apply',scene_id='city',run_id='stale',request_token='stale',position_cm=position,yaw_deg=0)
            raise AssertionError('Stale run accepted')
        except RPCError:pass
        air.rpc('flight.takeoff');airborne=True
        wait(lambda:device('uav-01')['position_cm'][2]>position[2]+100)
        wait(lambda:not air.rpc('sim.get_state')['command_active'])
        try:
            apply('uav-01',position,yaw)
            raise AssertionError('Airborne placement accepted')
        except RPCError:pass
        report['takeoff']=air.rpc('sim.get_state')
        air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready' and max(air.rpc('sim.get_state')['motor_rpm'])<1)
        airborne=False;wait(lambda:max(ue.rpc('sim.get_state')['motor_rpm'])<1)
        report['landed']=air.rpc('sim.get_state');report['passed']=True
    finally:
        if airborne:
            air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready' and max(air.rpc('sim.get_state')['motor_rpm'])<1)
        for ident in ('uav-01','ptz-01'):
            item=original[ident];apply(ident,item['position_cm'],item['placement_yaw_deg'])
        report['restored']=air.rpc('sim.get_state')
        (args.output/'live-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
