"""Exercise real paired baseline data, live rates, zoom and fusion inspection."""
import argparse
import json
from pathlib import Path
import time
from training_client.preview import QApplication, Window, QTimer
from training_client.client import Client
from training_client.fusion import comparison


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);app=QApplication([]);direct=Client(port=50051,device='ptz-01')
    original=direct.rpc('sim.get_state')
    def configure(sensor,fov):
        old=original['sensors'][sensor];payload=dict(sensor=sensor,enabled=old['enabled'],fov_deg=fov)
        if sensor=='infrared':payload.update(palette=old['palette'],noise=old['noise'])
        direct.rpc('sensor.configure',**payload)
    for sensor in ('visible','infrared'):configure(sensor,5)
    direct.rpc('gimbal.set_tracking',enabled=True)
    window=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=args.output/'dataset'))
    window.display_fps.setValue(2);window.save_fps.setValue(.5);window.record.setChecked(True);window.show();window.start()
    events=[];report=dict(passed=False,run_id=original['run_id'],phases={},comparisons={});start=time.monotonic();phase=0
    window.worker.metrics.connect(lambda item:events.append(dict(item,phase=phase)))
    def tick():
        nonlocal phase
        elapsed=time.monotonic()-start
        try:
            if elapsed>=7 and phase==0:
                assert window.latest and all(not tile.canvas.image.isNull() for tile in window.tiles.values()),window.state.text()
                report['comparisons']['raw']=comparison(window.latest,'raw')
                assert report['comparisons']['raw']['baseline_cm']>1
                window.grab().save(str(args.output/'raw-fusion.png'))
                window.display_fps.setValue(.5);window.save_fps.setValue(2);window.fusion_mode.setCurrentIndex(1)
                phase=1
            if elapsed>=14 and phase==1:
                assert window.latest and not window.tiles['fusion'].canvas.image.isNull()
                report['comparisons']['rotation']=comparison(window.latest,'rotation')
                assert report['comparisons']['rotation']['capture_delta_ms']==0
                window.grab().save(str(args.output/'rotation-fusion.png'))
                tile=window.tiles['fusion'];tile.enlarge();tile.popup.canvas.set_zoom(2);app.processEvents()
                tile.popup.grab().save(str(args.output/'enlarged-fusion.png'))
                for number in (0,1):
                    items=[i for i in events if i['phase']==number]
                    report['phases'][str(number)]=dict(received=len(items),displayed=sum(i['displayed'] for i in items),saved=sum(i['did_save'] for i in items))
                assert report['phases']['0']['displayed']>report['phases']['0']['saved']>=2
                assert report['phases']['1']['saved']>report['phases']['1']['displayed']>=1
                report['actual_rates_label']=window.actual_rates.text();report['passed']=True
                timer.stop();window.close();app.quit()
        except Exception as error:
            report['error']=repr(error);timer.stop();window.close();app.quit()
    timer=QTimer();timer.timeout.connect(tick);timer.start(100)
    try:app.exec()
    finally:
        for sensor in ('visible','infrared'):configure(sensor,original['sensors'][sensor]['fov_deg'])
        if original['tracking']:direct.rpc('gimbal.set_tracking',enabled=True)
        else:direct.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg'])
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    assert report['passed'],report
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
