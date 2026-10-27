"""Real AirSim regression: held keys must produce signed motion from hover.

Run with WISEYE UE/runner active: python -m tests.verify_manual_controls_live
Uses child-widget focus, held mouse buttons, release and window deactivation.
"""
import json
import math
import time
import apps.desktop_app.main
from PySide6.QtCore import Qt, QEvent, QCoreApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton
from core.config import ROOT, AppConfig
from apps.desktop_app.main_window import MainWindow

app=QApplication([])
window=MainWindow(AppConfig.load())
window.show()
checks=[]
report=dict(passed=False,keys=checks)

def wait(predicate, timeout=15):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if predicate(): return
        QTest.qWait(20)
    raise AssertionError(window.logs.toPlainText()[-2000:])

def position(): return list(window.air_state['position_ned_m'])

def settle():
    wait(lambda:window.air_state.get('last_manual_input')==[0,0,0,0])
    # SimpleFlight needs time to brake after held velocity commands. Verify
    # actual position stability instead of assuming a fixed braking duration.
    stable=0
    deadline=time.monotonic()+12
    previous=position()
    while time.monotonic()<deadline:
        QTest.qWait(550)
        current=position()
        stable=stable+1 if math.dist(previous,current)<.03 else 0
        if stable>=2: return
        previous=current
    raise AssertionError('Drone did not settle after release')

try:
    window.connect_ue()
    wait(lambda:window.client.ready and window.air_client.ready,60)
    if window.air_state.get('flight_status') == 'ready':
        window.command('flight.takeoff')
        wait(lambda:not window.air_state.get('command_active',True) and window.air_state.get('flight_status') != 'ready',30)
    window.flight.setCurrentIndex(1)
    window.flight.activated.emit(1)
    wait(lambda:window.air_state.get('flight_mode')=='manual' and not window.air_state['paused'])
    window.stop_manual_input()
    settle()
    window.fov.setFocus()
    initial=position()
    QTest.keyPress(window.fov,Qt.Key.Key_R)
    QTest.qWait(450)
    QTest.keyRelease(window.fov,Qt.Key.Key_R)
    assert not window.manual_keys and not window.manual_timer.isActive()
    assert window.air_state.get('last_manual_input')==[0,0,0,0]
    assert math.dist(initial,position())<.04
    report['numeric_editor_does_not_fly']=True
    specs=[(Qt.Key.Key_W,(1,0,0,0)),(Qt.Key.Key_S,(-1,0,0,0)),
           (Qt.Key.Key_A,(0,-1,0,0)),(Qt.Key.Key_D,(0,1,0,0)),
           (Qt.Key.Key_R,(0,0,1,0)),(Qt.Key.Key_F,(0,0,-1,0)),
           (Qt.Key.Key_Q,(0,0,0,-1)),(Qt.Key.Key_E,(0,0,0,1))]
    for key,vector in specs:
        window.setFocus()
        start=position()
        yaw_start=window.air_state['yaw_deg']
        count=window.air_state['manual_command_count']
        QTest.keyPress(window,key)
        wait(lambda:window.air_state.get('last_manual_input')==list(vector))
        QTest.qWait(1300)
        end=position()
        yaw_end=window.air_state['yaw_deg']
        assert window.air_state['manual_command_count']>=count+4
        QTest.keyRelease(window,key)
        delta=[b-a for a,b in zip(start,end)]
        yaw=math.radians(yaw_start)
        if vector[0]: projected=(delta[0]*math.cos(yaw)+delta[1]*math.sin(yaw))*vector[0]
        elif vector[1]: projected=(-delta[0]*math.sin(yaw)+delta[1]*math.cos(yaw))*vector[1]
        elif vector[2]: projected=-delta[2]*vector[2]
        else: projected=((yaw_end-yaw_start+180)%360-180)*vector[3]
        assert projected>(8 if vector[3] else .15),(key,delta,projected,window.air_state)
        checks.append(dict(key=key.name,input=vector,delta_ned_m=delta,signed_motion=projected))
        settle()
    button=next(b for b in window.findChildren(QPushButton) if b.text()=='前')
    before=window.air_state['manual_command_count']
    QTest.mousePress(button,Qt.MouseButton.LeftButton)
    wait(lambda:window.air_state.get('last_manual_input')==[1,0,0,0])
    QTest.qWait(700)
    QTest.mouseRelease(button,Qt.MouseButton.LeftButton)
    settle()
    assert window.air_state['manual_command_count']>before+3
    window.setFocus()
    QTest.keyPress(window,Qt.Key.Key_W)
    wait(lambda:window.air_state.get('last_manual_input')==[1,0,0,0])
    QCoreApplication.sendEvent(window,QEvent(QEvent.Type.WindowDeactivate))
    settle()
    assert not window.manual_keys
    start=position()
    QTest.qWait(700)
    drift=math.dist(start,position())
    assert drift<.2,drift
    report=dict(passed=True,keys=checks,held_mouse_button=True,focus_loss_stops=True,hover_drift_m=drift,numeric_editor_does_not_fly=True)
    (ROOT/'runtime/manual_controls_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)
except Exception as error:
    report['error']=repr(error)
    raise
finally:
    (ROOT/'runtime/manual_controls_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    window.stop_manual_input()
    window.close()
    app.processEvents()
