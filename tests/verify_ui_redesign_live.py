"""UI V3 regression against live services; restores sensor/control state and fleet bytes."""
import copy
import hashlib
import json
import socket
import sys
import time
from unittest.mock import patch
from pathlib import Path
import apps.desktop_app.main
from PySide6.QtCore import Qt, QPoint, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMessageBox
from core.config import ROOT, AppConfig
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.workbench_v3 import show_properties
from apps.desktop_app.route_editor import open_route_editor

app=QApplication([])
w=None
checks=[]
errors=[]
exceptions=[]
completed_all=False
screenshots=[]
old_hook=sys.excepthook
sys.excepthook=lambda typ,value,tb:exceptions.append(str(value))
store=QSettings('WISEYE','Studio')
saved_preferences={key:store.value(key) for key in ('workspace/v3','workbench/split')}
fleet_path=ROOT/'ue5/WISEYE/Config/WISEYE/Fleets/original.json'
fleet_bytes=fleet_path.read_bytes()


def rpc(command,payload=None):
    with socket.create_connection(('127.0.0.1',50051),5) as peer:
        peer.sendall((json.dumps(dict(version=1,request_id='ui-'+str(time.time_ns()),command=command,payload=payload or {}))+'\n').encode())
        response=json.loads(peer.makefile('rb').readline(16*1024*1024))
    assert response['status']=='ok',response
    return response['payload']


def wait(predicate,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        QTest.qWait(30)
        if exceptions:raise AssertionError(exceptions)
        if predicate():return
    raise AssertionError('UI condition timed out; '+str(errors[-4:]))


def passed(text):
    checks.append(text);print('PASS '+text,flush=True)


baseline=rpc('sim.get_state')
saved={d['id']:rpc('sim.get_state',{'device_id':d['id']}) for d in baseline['devices'] if d['kind']=='gimbal'}
try:
    w=MainWindow(AppConfig.load());w.resize(1600,1000);w.show();w.gallery.reset_layout()
    w.client.failed.connect(lambda command,message:errors.append((command,message)))
    w.connect_ue();wait(lambda:w.client.ready and w.air_client.ready and w.simulation_healthy,40)
    wait(lambda:len(w.gallery.frames)==3,45)
    assert (w.gallery.frames['ptz-01/visible'].width(),w.gallery.frames['ptz-01/visible'].height())==(1920,1080)
    assert (w.gallery.frames['ptz-01/infrared'].width(),w.gallery.frames['ptz-01/infrared'].height())==(640,512)
    passed('scene-led default shows native 1920x1080 visible and 640x512 IR with one decoder each')
    clients=dict(w.gallery.clients);sources=list(w.gallery.sources)
    show_properties(w,'drone','uav-02')
    assert w.selected_drone=='uav-01' and w.inspector_takeover.isVisible()
    show_properties(w,'sensor','ptz-02/infrared')
    wait(lambda:w.sensor_settings.panels['infrared']['confirmed'] is not None)
    assert w.selected_gimbal=='ptz-01' and w.gallery.sources==sources
    w.fleet_selection.select('gimbal','ptz-02');wait(lambda:w.state.get('gimbal_id')=='ptz-02')
    assert w.gallery.sources==sources and all(w.gallery.clients[k] is v for k,v in clients.items())
    w.fleet_selection.select('gimbal','ptz-01');wait(lambda:w.state.get('gimbal_id')=='ptz-01')
    passed('property selection never takes flight control; switching PTZ preserves fixed streams and decoders')
    w.gallery.add_source('ptz-02/infrared',replace='ptz-01/infrared')
    wait(lambda:'ptz-02/infrared' in w.gallery.frames,35)
    assert 'ptz-02/CH2' in w.gallery.clients['ptz-02/infrared'].url
    client=w.gallery.clients['ptz-02/infrared']
    w.gallery.enlarge('ptz-02/infrared');QTest.qWait(200)
    assert len(w.gallery.clients)==3 and w.gallery.clients['ptz-02/infrared'] is client
    assert not w.gallery.popouts['ptz-02/infrared'][1].source.isNull()
    w.gallery.maximize('ptz-02/infrared');QTest.qWait(100)
    assert w.gallery.cards['ptz-02/infrared'].isVisible() and not w.gallery.cards['scene/observer'].isVisible()
    w.gallery.maximize('ptz-02/infrared');w.gallery.popouts['ptz-02/infrared'][0].close()
    w.gallery.swap('scene/observer','ptz-01/visible');assert w.gallery.mode=='custom'
    w.gallery.swap('ptz-01/visible','scene/observer')
    passed('cross-PTZ tiles, shared popout, maximize/return and drag-order logic retain source identity')

    forms=w.sensor_settings
    forms.select_device('ptz-01');wait(lambda:forms.panels['visible']['confirmed'] is not None)
    forms.panels['visible']['fields']['fov_deg'].setValue(37)
    forms.select_device('ptz-02');wait(lambda:forms.panels['visible']['confirmed'] is not None)
    forms.panels['visible']['fields']['fov_deg'].setValue(53);forms.submit('visible')
    forms.select_device('ptz-01');forms.panels['visible']['fields']['fov_deg'].setValue(39)
    wait(lambda:not forms.pending)
    assert forms.values('visible')['fov_deg']==39 and forms.panels['visible']['dirty']
    assert abs(rpc('sim.get_state',{'device_id':'ptz-02'})['sensors']['visible']['fov_deg']-53)<.01
    forms.submit('visible');forms.panels['visible']['fields']['fov_deg'].setValue(40)
    wait(lambda:not forms.pending)
    assert forms.values('visible')['fov_deg']==40 and forms.panels['visible']['dirty']
    assert abs(forms.panels['visible']['confirmed']['fov_deg']-39)<.01
    forms.restore('visible');assert forms.values('visible')['fov_deg']==39
    passed('device-specific drafts and request IDs isolate late acknowledgements; edits during apply survive')
    forms.select_device('ptz-02')
    forms.panels['infrared']['fields']['enabled'].setChecked(False);forms.submit('infrared');wait(lambda:not forms.pending)
    wait(lambda:'ptz-02/infrared' not in w.gallery.frames)
    assert 'ptz-01/visible' in w.gallery.frames
    forms.panels['infrared']['fields']['enabled'].setChecked(True);forms.submit('infrared');wait(lambda:not forms.pending)
    wait(lambda:'ptz-02/infrared' in w.gallery.frames,30)
    passed('one sensor enable/disable changes only its source and restarts its decoder when re-enabled')
    rpc('input.set_mode',{'mode':'gimbal'});rpc('gimbal.set_angles',{'device_id':'ptz-01','yaw_deg':0,'pitch_deg':5})
    wait(lambda:w.state.get('input_mode')=='gimbal')
    show_properties(w,'gimbal','ptz-01');w.setFocus()
    QTest.keyPress(w,Qt.Key.Key_Right);QTest.qWait(650);QTest.keyRelease(w,Qt.Key.Key_Right)
    wait(lambda:w.state['yaw_deg']>5);QTest.qWait(400)
    stopped=w.state['yaw_deg'];QTest.qWait(600);assert abs(w.state['yaw_deg']-stopped)<.5
    w.gimbal_yaw.setFocus();QTest.keyClick(w.gimbal_yaw,Qt.Key.Key_Up);QTest.qWait(500)
    assert abs(w.state['yaw_deg']-stopped)<.5
    passed('arrow control moves actual gimbal; key release stops; spinbox editing does not drive it')

    rpc('input.set_mode',{'mode':'observer'});rpc('observer.set_mode',{'mode':'free'})
    wait(lambda:w.state.get('input_mode')=='observer' and w.state.get('observer_mode')=='free')
    w.gallery.reset_layout();QTest.qWait(300)
    view=w.gallery.views['scene/observer'];before=w.state['observer_position_cm'][:]
    QTest.mousePress(view,Qt.MouseButton.RightButton,pos=QPoint(60,60));QTest.keyPress(view,Qt.Key.Key_W);QTest.qWait(600)
    QTest.keyRelease(view,Qt.Key.Key_W);QTest.mouseRelease(view,Qt.MouseButton.RightButton,pos=QPoint(60,60))
    wait(lambda:sum(abs(a-b) for a,b in zip(before,w.state['observer_position_cm']))>50)
    QTest.qWait(400);stopped=w.state['observer_position_cm'][:];QTest.qWait(600)
    assert sum(abs(a-b) for a,b in zip(stopped,w.state['observer_position_cm']))<1
    passed('embedded observer right-button keyboard movement still moves camera and stops on release')
    open_route_editor(w);editor=w.route_editor
    editor.name.setText('UI V3 draft test')
    before=len(w.air_client.pending);editor.start_route();assert '先上传' in editor.status.text()
    assert len(w.air_client.pending)==before
    editor.table.item(0,0).setText('nan');editor.upload();assert '数字' in editor.status.text()
    editor.close()
    passed('route draft, upload and execution are separate; invalid or unuploaded drafts cannot execute')
    w.pages.setCurrentIndex(1);show_properties(w,'drone','uav-01')
    w.gallery.reset_layout();wait(lambda:len(w.gallery.frames)==3,30)
    for width,height in [(1920,1080),(1600,900),(1280,720)]:
        target_height=min(height,app.primaryScreen().availableGeometry().height()-40)
        w.resize(width,target_height);QTest.qWait(400)
        assert w.width()==width and abs(w.height()-target_height)<25
        assert w.gallery.width()>450
        path=f'docs/evidence/ui_redesign_{w.width()}x{w.height()}_20261021.png'
        w.grab().save(str(ROOT/path));screenshots.append(dict(path=path,width=w.width(),height=w.height()))
    w.resize(1600,1000)
    w.pages.setCurrentIndex(2);QTest.qWait(200);assert w.source_table.rowCount()>=7
    assert not w.gallery.clients,'hidden workbench retains unnecessary decoders'
    w.grab().save(str(ROOT/'docs/evidence/ui_redesign_interfaces_20261021.png'))
    w.pages.setCurrentIndex(1);show_properties(w,'sensor','ptz-02/infrared');QTest.qWait(400)
    wait(lambda:len(w.gallery.frames)==3,35)
    w.grab().save(str(ROOT/'docs/evidence/ui_redesign_parameters_20261021.png'))
    passed('three window sizes and data-source table render with collapsible panels and per-source controls')
    assert not errors and not exceptions,(errors,exceptions)
    completed_all=True
finally:
    if w:
        # Restore actual device configuration without modifying fleet/map files.
        for device,state in saved.items():
            for sensor,settings in state['sensors'].items():rpc('sensor.configure',dict(device_id=device,sensor=sensor,**settings))
            rpc('gimbal.set_angles',dict(device_id=device,yaw_deg=state['yaw_deg'],pitch_deg=state['pitch_deg']))
            rpc('gimbal.set_target',dict(device_id=device,drone_id=state['tracking_target']))
            rpc('gimbal.set_tracking',dict(device_id=device,enabled=state['tracking']))
        rpc('input.select_gimbal',{'gimbal_id':baseline.get('gimbal_id','ptz-01')})
        rpc('input.set_mode',{'mode':baseline['input_mode']})
        rpc('observer.set_mode',{'mode':baseline['observer_mode']})
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.close()
        app.processEvents()
    for key,value in saved_preferences.items():
        if value is None:store.remove(key)
        else:store.setValue(key,value)
    sys.excepthook=old_hook
    assert fleet_path.read_bytes()==fleet_bytes,'User fleet was modified'
    (ROOT/'docs/evidence/ui_redesign_live_20261021.json').write_text(json.dumps(dict(success=completed_all,checks=checks,passed=len(checks),errors=errors,exceptions=exceptions,screenshots=screenshots,fleet_sha256=hashlib.sha256(fleet_bytes).hexdigest()),ensure_ascii=False,indent=2),encoding='utf-8')
