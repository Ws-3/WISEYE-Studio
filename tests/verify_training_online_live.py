"""Online policy/output/source changes on an explicitly owned test run."""
import argparse
import json
from pathlib import Path
import time
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from training_client.client import Client
from training_client.workbench import Window


def main():
    p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    owned=json.loads(args.ready.read_text());ue=Client(port=50051);original=ue.rpc('sim.get_state');assert original['run_id']==owned['run_id']
    app=QApplication.instance() or QApplication([])
    w=Window(argparse.Namespace(host='127.0.0.1',port=50100,device='ptz-01',output=args.output/'unused-old'))
    report=dict(passed=False,run_id=owned['run_id']);args.output.mkdir(parents=True,exist_ok=True)
    def wait(predicate,seconds=20):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            app.processEvents()
            if predicate():return
            time.sleep(.02)
        raise TimeoutError(w.state.text()+' / '+w.settings_status.text())
    def annotations(folder):return list(folder.glob('*/annotations/*.json'))
    try:
        ue.rpc('gimbal.set_angles',yaw_deg=0,pitch_deg=25)
        w.show();w.start();wait(lambda:w.latest is not None and len(w.latest['samples'])==2)
        first=w.worker;folder=args.output/'online-paired'
        w.occlusion.setChecked(False);w.outside.setChecked(False)
        w.directory.setText(str(folder));w.directory.editingFinished.emit()
        assert w.worker is first
        assert all(control.isEnabled() for control in (w.occlusion,w.outside,w.directory,w.visible,w.infrared,w.host,w.port,w.device))
        w.record.setChecked(True);wait(lambda:len(annotations(folder))>=2)
        for path in annotations(folder):
            item=json.loads(path.read_text(encoding='utf8'))
            assert not item['gt_policy']['keep_partial_occlusion'] and not item['gt_policy']['keep_partial_outside']
        assert not annotations(args.output/'unused-old')
        report['policy_and_directory_live']=True
        w.show_gt.setChecked(False);wait(lambda:w.latest is not None)
        w.infrared.setChecked(False)
        wait(lambda:w.worker is not None and w.worker is not first and w.worker.sensors==('visible',) and w.latest is not None and len(w.latest['samples'])==1)
        assert w.tiles['infrared'].canvas.image.isNull()
        report['automatic_source_switch']=True
        current=w.worker;w.connect.click()
        wait(lambda:w.worker is not None and w.worker is not current and w.latest is not None)
        assert w.record.isChecked() and not w.occlusion.isChecked()
        report['connection_apply_preserves_settings']=True
        w.grab().save(str(args.output/'training-online.png'));report['passed']=True
    finally:
        w.close();wait(lambda:w.worker is None)
        ue.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg'])
        ue.rpc('gimbal.set_tracking',enabled=original['tracking'])
        (args.output/'training-live.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
