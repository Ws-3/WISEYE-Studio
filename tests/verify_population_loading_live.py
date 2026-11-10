"""Owned small-city load, dense passive agents and camera sweep; no takeoff."""
import os,time,json,math,statistics
from pathlib import Path

def main():
    assert 'aerial-population-test-data' in os.environ.get('WISEYE_DATA_DIR','')
    import apps.desktop_app.main
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtCore import QSettings
    from unittest.mock import patch
    from core.config import AppConfig
    from core.local_rpc import request
    from apps.desktop_app.main_window import MainWindow
    out=Path('builds/population-loading-live');out.mkdir(exist_ok=True)
    app=QApplication([]);QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(out/'qt'))
    w=MainWindow(AppConfig.load());w.show();report={'passed':False};phases=[]
    def settle(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds=90):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents()
            try:
                if predicate():return
            except OSError:pass
            time.sleep(.04)
        raise TimeoutError('Population/loading acceptance timeout')
    def rpc(command,**args):
        r=request(50051,command,args,timeout=4);assert r['status']=='ok',r
        return r['payload']
    def state():return rpc('sim.get_state')
    try:
        w.scenes.setCurrentIndex(next(i for i in range(w.scenes.count()) if (w.scenes.itemData(i) or {}).get('id')=='city'))
        w.launch_ue();w.runtime_manager.phase.connect(lambda stage,detail:phases.append([stage,detail]))
        assert w.loading_screen.active;settle(.3);w.grab().save(str(out/'loading-start.png'))
        wait(lambda:w.client.ready and w.air_client.ready and not w.loading_screen.active,900)
        assert not w.loading_screen.pulse.timer.isActive();report['initial']=state();print('Real loading finished',flush=True)
        rpc('population.configure',vehicles_enabled=True,pedestrians_enabled=True,vehicle_density=.5,pedestrian_density=.5)
        wait(lambda:not state()['population']['pending'],120)
        agents=rpc('population.get_agents');report['agents']=agents;settle(3);later=rpc('population.get_agents')
        for kind in ('vehicle','pedestrian'):
            old={s['target_id']:s['position_cm'] for s in agents[kind]['samples']}
            assert any(x['target_id'] in old and math.dist(x['position_cm'],old[x['target_id']])>10 for x in later[kind]['samples']),kind+' not moving'
        for kind,count in [('vehicle',300),('parked_vehicle',300),('pedestrian',600)]:assert agents[kind]['active_entities']==count,(kind,agents[kind]['active_entities'])
        report['agents_later']=later;w.mission_workspace.open_aerial('uav-02');d=w.aerial_dialog;wait(lambda:d.valid)
        wait(lambda:'uav-02/aerial' in w.gallery.frames)
        samples=[];stamps=set()
        for _ in range(24):
            d.nudge('yaw_deg',5);settle(.5);s=state();hw=s['runtime_hardware']
            if hw['sample_time_s'] not in stamps:stamps.add(hw['sample_time_s']);samples.append(hw)
        report['samples']=samples;fps=[s['ue_fps'] for s in samples];report['fps']={'median':statistics.median(fps),'min':min(fps),'samples':len(fps)}
        report['final']=state();report['phases']=phases;report['loading_animation_stopped']=True
        w.grab().save(str(out/'dense-workbench.png'));w.gallery.frames['uav-02/aerial'].save(str(out/'dense-aerial.png'))
        report['passed']=True;print('Dense agents, movement and camera sweep passed',flush=True)
    finally:
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        wait(lambda:not w.runtime_manager.running,140);report['owned_session_stopped']=True
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');app.quit()

if __name__=='__main__':main()
