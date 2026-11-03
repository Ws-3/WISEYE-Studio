"""Unified matched preview, overlay-only toggle and saved GT on an owned run."""
import argparse
import json
from pathlib import Path
import statistics
import time
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from training_client.client import Client
from training_client.workbench import Window
from training_client.train import collect


def main():
    p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    owned=json.loads(args.ready.read_text());ue=Client(port=50051);air=Client(port=50052,device='uav-01')
    original=ue.rpc('sim.get_state');assert original['run_id']==owned['run_id']
    app=QApplication.instance() or QApplication([]);w=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=args.output/'dataset'))
    report=dict(passed=False,run_id=owned['run_id']);args.output.mkdir(parents=True,exist_ok=True);airborne=False;times=[];seen=set()
    def wait(predicate,seconds=70):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            app.processEvents()
            if predicate():return
            time.sleep(.01)
        raise TimeoutError(w.state.text())
    def run_for(seconds,moving=False):
        until=time.monotonic()+seconds;next_input=0;latencies=[]
        while time.monotonic()<until:
            app.processEvents()
            if w.latest:
                pair=w.latest;packet=pair['samples']['visible']
                assert packet['simulation_time_s']==pair['samples']['infrared']['simulation_time_s']
                if packet['frame_id'] not in seen:seen.add(packet['frame_id']);times.append(time.monotonic())
            if moving and time.monotonic()>=next_input:
                start=time.monotonic();air.rpc('flight.set_input',forward=.05,right=0,up=0,yaw=0)
                latencies.append(1000*(time.monotonic()-start));next_input=time.monotonic()+.2
            time.sleep(.01)
        return latencies
    try:
        air.rpc('flight.takeoff');airborne=True;wait(lambda:not air.rpc('sim.get_state')['command_active'])
        ue.rpc('gimbal.set_tracking',enabled=True);time.sleep(.5)
        w.record.setChecked(True);w.show();w.start();worker=w.worker
        wait(lambda:w.latest is not None,15);run_for(3)
        assert not hasattr(w,'view_mode') and not hasattr(w,'video_fps')
        assert all(not tile.canvas.image.isNull() for tile in w.tiles.values())
        assert any(p['objects'] for p in w.latest['samples'].values())
        w.grab().save(str(args.output/'gt-on.png'))
        identity=w.latest['pair_id'];w.show_gt.setChecked(False)
        assert w.latest['pair_id']==identity and w.worker is worker
        for sensor in ('visible','infrared'):assert w.tiles[sensor].canvas.image==w.decoded[sensor]
        air.rpc('flight.set_mode',mode='manual');wait(lambda:not air.rpc('sim.get_state')['command_active'])
        delays=run_for(4,moving=True);air.rpc('flight.set_input',forward=0,right=0,up=0,yaw=0)
        run_for(1);w.grab().save(str(args.output/'gt-off.png'))
        paths=list((args.output/'dataset').glob('IR/labels/*.txt'));assert len(paths)>=4 and any(p.read_text().strip() for p in paths)
        assert collect(args.output/'dataset','infrared')[0]
        report.update(passed=True,displayed_pairs=len(times),displayed_fps=(len(times)-1)/(times[-1]-times[0]),saved_pairs=len(paths),overlay_only=True,gt_labels_preserved_while_hidden=True,manual_input_median_ms=statistics.median(delays))
    finally:
        w.close();wait(lambda:w.worker is None,15)
        if airborne:
            air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready' and max(air.rpc('sim.get_state')['motor_rpm'])<1)
        ue.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']);ue.rpc('gimbal.set_tracking',enabled=original['tracking'])
        report['final']=air.rpc('sim.get_state')
        (args.output/'unified-live.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='final'},indent=2),flush=True)


if __name__=='__main__':main()
