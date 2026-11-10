"""Owned UI test of live camera aiming, with no takeoff or normal-data writes."""
import os,time,json
from pathlib import Path

def main():
    assert 'aerial-population-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    from PySide6.QtCore import QSettings,Qt
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtTest import QTest
    from unittest.mock import patch
    from apps.desktop_app.main_window import MainWindow
    from apps.desktop_app.observation_panel import open_aerial
    from core.config import AppConfig
    from core.local_rpc import request
    out=Path('builds/aerial-aim-live');out.mkdir(exist_ok=True)
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();report={'passed':False}
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,timeout=90):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            app.processEvents()
            try:
                if predicate():return
            except OSError:pass
            time.sleep(.03)
        raise TimeoutError('Aerial live aim timeout')
    def state():
        r=request(50051,'sim.get_state',timeout=3);assert r['status']=='ok',r
        return r['payload']
    def camera():return next(d['aerial'] for d in state()['devices'] if d['id']=='uav-02')
    try:
        w.scenes.setCurrentIndex(next(i for i in range(w.scenes.count()) if (w.scenes.itemData(i) or {}).get('id')=='city'))
        w.launch_ue();print('Launching owned city',flush=True)
        wait(lambda:w.client.ready and w.air_client.ready,900)
        wait(lambda:not state()['population']['pending'] and state()['runtime_hardware'].get('asset_compile_jobs',0)==0,900)
        if not w.client.ready:w.connect_ue()
        wait(lambda:w.client.ready)
        report['initial']=state();selected=w.selected_drone
        open_aerial(w,'uav-02');d=w.aerial_dialog;wait(lambda:d.valid)
        d.preview.click();wait(lambda:'uav-02/aerial' in w.gallery.frames)
        d.fields['pitch_deg'].setValue(-30);d.fields['yaw_deg'].setValue(0)
        wait(lambda:d.pending is None and not d.dirty and camera()['pitch_deg']==-30)
        settle(1);before=w.gallery.frames['uav-02/aerial'].copy();before.save(str(out/'before.png'))
        QTest.mousePress(d.aim_buttons[3],Qt.MouseButton.LeftButton);settle(.9);QTest.mouseRelease(d.aim_buttons[3],Qt.MouseButton.LeftButton)
        expected=d.fields['yaw_deg'].value();assert expected>=8
        wait(lambda:d.pending is None and not d.dirty and camera()['yaw_deg']==expected)
        d.fields['pitch_deg'].setValue(-75)
        wait(lambda:d.pending is None and not d.dirty and camera()['pitch_deg']==-75)
        settle(1);after=w.gallery.frames['uav-02/aerial'];after.save(str(out/'after.png'))
        assert before!=after,'Camera image did not change'
        assert w.selected_drone==selected,'Camera adjustment took over flight selection'
        report['final_camera']=camera();report['final']=state();report['held_yaw_deg']=expected
        d.grab().save(str(out/'controls.png'));w.grab().save(str(out/'workbench.png'))
        report['passed']=True;print('Live pitch, held yaw and independent selection passed',flush=True)
    finally:
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        wait(lambda:not w.runtime_manager.running,140);report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');app.quit()

if __name__=='__main__':main()
