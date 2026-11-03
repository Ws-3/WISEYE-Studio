"""Compare matched GT rates and native progress only on an owned UE session."""
import argparse
import json
import statistics
from pathlib import Path
import threading
import time
from training_client.client import Client


def main():
    p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rates',type=float,nargs='+',default=[2,5,10,20]);p.add_argument('--seconds',type=float,default=15);args=p.parse_args()
    owned=json.loads(args.ready.read_text());native=Client(port=50051);client=Client();state=native.rpc('sim.get_state')
    assert state['run_id']==owned['run_id'];report=dict(passed=False,run_id=state['run_id'],phases=[])
    end=threading.Event();telemetry=[];air=Client(port=50052,device='uav-01');airborne=False
    def monitor():
        probe=Client(port=50051)
        while not end.is_set():
            t=time.monotonic()
            try:
                current=probe.rpc('sim.get_state');telemetry.append((t,current,time.monotonic()-t))
            except Exception:pass
            end.wait(.5)
    thread=threading.Thread(target=monitor);thread.start()
    def summary(start,stop):
        rows=[r for r in telemetry if start<=r[0]<=stop]
        a,b=rows[0],rows[-1];duration=b[0]-a[0]
        return dict(tick_fps=(b[1]['tick_seq']-a[1]['tick_seq'])/duration,
            native_rtt_ms=1000*statistics.median(r[2] for r in rows),
            source_fps={c:(b[1]['streams'][c]['completed_frames']-a[1]['streams'][c]['completed_frames'])/duration for c in ('CH1','CH2')},
            hardware=b[1].get('runtime_hardware',{}))
    try:
        air.rpc('flight.takeoff');airborne=True
        deadline=time.monotonic()+70
        while air.rpc('sim.get_state')['command_active']:
            assert time.monotonic()<deadline;time.sleep(.2)
        native.rpc('gimbal.set_tracking',enabled=True);time.sleep(1)
        start=time.monotonic();time.sleep(8);report['baseline']=summary(start,time.monotonic())
        for fps in args.rates:
            client.configure(max_fps=fps);client.sample_pair();time.sleep(.6)
            started=time.monotonic();returned=[];latencies=[];cpu=[];visible_frames=set();targets=[]
            while time.monotonic()-started<args.seconds:
                requested=time.monotonic();pair=client.sample_pair();now=time.monotonic()
                samples=pair['samples'];assert samples['visible']['simulation_time_s']==samples['infrared']['simulation_time_s']
                assert pair['pair_id']==samples['visible']['sample_token']==samples['infrared']['sample_token']
                assert samples['visible']['frame_id'] not in visible_frames;visible_frames.add(samples['visible']['frame_id'])
                returned.append(now);latencies.append(1000*(now-requested));cpu.extend(s['gt_annotation_cpu_ms'] for s in samples.values())
                targets.append(sum(len(s['objects']) for s in samples.values()))
                remaining=1/fps-(time.monotonic()-requested)
                if remaining>0:time.sleep(remaining)
            phase=dict(requested_fps=fps,pairs=len(returned),actual_fps=(len(returned)-1)/(returned[-1]-returned[0]),
                round_trip_median_ms=statistics.median(latencies),round_trip_p95_ms=sorted(latencies)[int(.95*(len(latencies)-1))],
                annotation_cpu_median_ms=statistics.median(cpu),pairs_with_gt=sum(v>0 for v in targets),**summary(started,time.monotonic()))
            report['phases'].append(phase);print(json.dumps(phase),flush=True)
        report['passed']=True
    finally:
        if airborne:
            air.rpc('flight.land');deadline=time.monotonic()+70
            while air.rpc('sim.get_state')['flight_status']!='ready':
                assert time.monotonic()<deadline;time.sleep(.2)
        native.rpc('gimbal.set_angles',yaw_deg=state['yaw_deg'],pitch_deg=state['pitch_deg'])
        native.rpc('gimbal.set_tracking',enabled=state['tracking'])
        end.set();thread.join(3);client.configure(max_fps=2)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('GT_RATE_BENCHMARK_PASSED',flush=True)


if __name__=='__main__':main()
