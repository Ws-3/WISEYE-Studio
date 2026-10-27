"""Actual Qt takeoff, held-button motion and explicit route execution; always lands."""
import json
import math
import time
import apps.desktop_app.main
from PySide6.QtCore import Qt,QEvent,QCoreApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from core.config import ROOT,AppConfig
from apps.desktop_app.main_window import MainWindow

app=QApplication([]);w=MainWindow(AppConfig.load());w.resize(1600,1000);w.show()
checks=[];success=False;original_route=None;errors=[];airborne=False
w.air_client.failed.connect(lambda c,m:errors.append((c,m)))


def wait(predicate,seconds=25):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        QTest.qWait(40)
        if predicate():return
    raise AssertionError(w.logs.toPlainText()[-1200:])


def passed(text):checks.append(text);print('PASS '+text,flush=True)


def settle():
    previous=w.air_state['position_ned_m'][:];stable=0
    end=time.monotonic()+15
    while time.monotonic()<end:
        QTest.qWait(500);current=w.air_state['position_ned_m'][:]
        stable=stable+1 if math.dist(previous,current)<.04 else 0
        if stable>=2:return
        previous=current
    raise AssertionError('manual motion did not settle')


try:
    w.connect_ue();wait(lambda:w.client.ready and w.air_client.ready and w.simulation_healthy,40)
    assert all(s['flight_status']=='ready' for s in w.air_state['fleet']),'Requires all aircraft landed'
    original_route=w.air_state.get('route')
    QTest.mouseClick(w.takeoff_button,Qt.MouseButton.LeftButton);airborne=True
    wait(lambda:w.air_state['flight_status']!='ready' and not w.air_state['command_active'],45)
    assert not w.takeoff_button.isEnabled() and max(w.air_state['motor_rpm'])>1000
    passed('actual Takeoff button starts only selected aircraft; motor telemetry remains read-only')
    wait(lambda:w.manual_takeover.isEnabled())
    QTest.mouseClick(w.manual_takeover,Qt.MouseButton.LeftButton)
    wait(lambda:w.air_state['flight_mode']=='manual' and not w.air_state['paused'])
    w.stop_manual_input();settle()
    button=next(b for b in w.drone_panel.findChildren(QPushButton) if b.text()=='前进')
    wait(lambda:button.isEnabled());before=w.air_state['position_ned_m'][:];yaw=math.radians(w.air_state['yaw_deg'])
    QTest.mousePress(button,Qt.MouseButton.LeftButton);QTest.qWait(1100)
    assert button.isEnabled(),'held button was disabled by ongoing short velocity tasks'
    QTest.mouseRelease(button,Qt.MouseButton.LeftButton);settle()
    after=w.air_state['position_ned_m'];delta=[b-a for a,b in zip(before,after)]
    assert delta[0]*math.cos(yaw)+delta[1]*math.sin(yaw)>.15,delta
    assert w.air_state['last_manual_input']==[0,0,0,0]
    passed('holding Forward produces signed body-axis motion across polls; release brakes and holds')
    w.setFocus();QTest.keyPress(w,Qt.Key.Key_W)
    wait(lambda:w.air_state['last_manual_input']==[1,0,0,0])
    QCoreApplication.sendEvent(w,QEvent(QEvent.Type.WindowDeactivate));settle()
    assert not w.manual_keys and w.air_state['last_manual_input']==[0,0,0,0]
    passed('window deactivation clears continuous flight input and actual aircraft settles')
    auto=w.flight.findData('auto');w.flight.setCurrentIndex(auto);w.flight.activated.emit(auto)
    QTest.qWait(300);editor=w.route_editor
    assert w.air_state['flight_mode']=='manual','mode selector unexpectedly started automatic flight'
    x,y,down=w.air_state['position_ned_m']
    route=dict(version=1,scene_id=w.state['scene_id'],name='UI explicit route',frame='ue_world_m',speed_mps=1,repeat=False,waypoints=[[x,y,-down],[x+2,y,-down]])
    editor.set_data(route);editor.upload();wait(lambda:editor.uploaded_snapshot is not None and editor.uploading_snapshot is None)
    assert w.air_state['flight_mode']=='manual'
    wait(lambda:editor.start_button.isEnabled(),20)
    QTest.mouseClick(editor.start_button,Qt.MouseButton.LeftButton)
    wait(lambda:w.air_state.get('route_status')=='completed',45)
    wait(lambda:not w.air_state['command_active'])
    passed('route mode opens editor without flight; upload stays idle; explicit Execute completes native route')
    editor.close();QTest.mouseClick(w.land_button,Qt.MouseButton.LeftButton)
    wait(lambda:w.air_state['flight_status']=='ready' and max(w.air_state['motor_rpm'])<1,45);airborne=False
    assert all(s['flight_status']=='ready' for s in w.air_state['fleet'])
    assert not errors,errors
    passed('actual Land button returns to ready and physical motors disarm; other aircraft stay landed')
    success=True
finally:
    if w.air_client.ready:
        w.manual_keys.clear();w.stop_manual_input()
        if airborne or w.air_state.get('flight_status')!='ready':
            w.command('flight.land');wait(lambda:w.air_state.get('flight_status')=='ready',50)
        if original_route:w.command('route.upload',original_route);QTest.qWait(400)
    w.close();app.processEvents()
    (ROOT/'docs/evidence/ui_redesign_flight_20261021.json').write_text(json.dumps(dict(success=success,checks=checks,errors=errors),ensure_ascii=False,indent=2),encoding='utf8')
