"""Real desktop auto-apply, isolated saved poses and no map reload."""
import argparse
import json
import math
import os
from pathlib import Path
import time
import uuid


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ready',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    owned=json.loads(args.ready.read_text());data=Path(owned['data'])
    assert data.name=='live-placement-data'
    os.environ['WISEYE_DATA_DIR']=str(data);os.environ['WISEYE_RESOURCES_DIR']=str(Path(__file__).resolve().parents[1])
    import apps.desktop_app.main
    from PySide6.QtWidgets import QApplication
    from core.config import AppConfig
    from apps.desktop_app.main_window import MainWindow
    from training_client.client import Client
    app=QApplication.instance() or QApplication([]);w=MainWindow(AppConfig());args.output.mkdir(parents=True,exist_ok=True)
    files=[data/'ue5/WISEYE/Config/WISEYE/Fleets/city.json',data/'ue5/WISEYE/Config/WISEYE/Layouts/city.json']
    saved={path:path.read_bytes() for path in files}
    original=Client(port=50051).rpc('sim.get_state');assert original['run_id']==owned['run_id']
    devices={d['id']:d for d in original['devices']};report=dict(passed=False,run_id=owned['run_id'])
    def wait(predicate,limit=15):
        deadline=time.monotonic()+limit
        while time.monotonic()<deadline:
            app.processEvents()
            if predicate():return
            time.sleep(.02)
        raise TimeoutError(w.arrangement.message.text())
    def device(ident):return next(d for d in w.state['devices'] if d['id']==ident)
    try:
        for index in range(w.scenes.count()):
            if w.scenes.itemData(index)['id']=='city':w.scenes.setCurrentIndex(index);break
        w.show();w.connect_ue();wait(lambda:w.client.ready and w.air_client.ready and w.state.get('run_id')==owned['run_id'])
        w.pages.setCurrentIndex(0)
        for ident in ('ptz-01','uav-01'):
            key=w.arrangement.coordinate_key(ident);old=devices[ident]
            wanted=[old['position_cm'][0]+30,*old['position_cm'][1:]];yaw=old['placement_yaw_deg']+3
            for field,value in zip(w.arrangement.coordinates[key],wanted):field.setValue(value/100)
            w.arrangement.yaw_fields[key].setValue(yaw)
            wait(lambda:not w.arrangement.tools.apply_pending and math.dist(device(ident)['position_cm'][:2],wanted[:2])<1 and abs(device(ident)['placement_yaw_deg']-yaw)<.01)
            assert w.state['run_id']==owned['run_id']
            report[ident]=dict(position=device(ident)['position_cm'],yaw=yaw,message=w.arrangement.message.text())
        w.arrangement.save()
        persisted=json.loads(files[0].read_text(encoding='utf-8-sig'))
        assert all(abs(d['rotation_deg'][1]-devices[d['id']]['placement_yaw_deg']-3)<.01 for d in persisted['devices'])
        w.grab().save(str(args.output/'desktop-live-placement.png'))
        report['passed']=True
    finally:
        w.arrangement.tools.live.setChecked(False);w.arrangement.tools.apply_timer.stop()
        for ident,item in devices.items():
            c=Client(port=50052 if ident.startswith('uav-') else 50051,device=ident)
            c.rpc('placement.apply',scene_id='city',run_id=owned['run_id'],request_token=uuid.uuid4().hex,
                  position_cm=item['position_cm'],yaw_deg=item['placement_yaw_deg'])
        for path,content in saved.items():path.write_bytes(content)
        w.client.ready=False;w.close();app.processEvents()
        (args.output/'gui-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
