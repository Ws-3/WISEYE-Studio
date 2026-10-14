"""Run from the repo with: python -m tests.verify_desktop_live (UE PIE required)."""
import json
import socket
import time
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from PySide6.QtNetwork import QTcpServer, QHostAddress
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from core.config import ROOT, AppConfig
from core.protocol import encode_request
from apps.desktop_app.client import UEClient
from apps.desktop_app.main_window import MainWindow

app=QApplication([])
window=MainWindow(AppConfig.load())
window.show()
checks=[]
heartbeats=[]
timer=QTimer()
timer.setInterval(25)
timer.timeout.connect(lambda:heartbeats.append(time.monotonic()))
timer.start()

def wait(predicate,timeout=8):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        app.processEvents()
        if predicate(): return
        QTest.qWait(20)
    raise AssertionError('Timed out waiting for UI/UE state')

def click(button): QTest.mouseClick(button,Qt.MouseButton.LeftButton)

try:
    click(window.connect_button)
    wait(lambda:window.client.ready and bool(window.state),45)
    checks.append('real UE handshake and state polling')
    if window.state['paused']:
        click(window.resume_button); wait(lambda:not window.state['paused'])
    click(window.pause_button)
    wait(lambda:window.state['paused'])
    paused_time=window.state['simulation_time_s']
    QTest.qWait(700)
    assert abs(window.state['simulation_time_s']-paused_time)<.001
    click(window.resume_button)
    wait(lambda:not window.state['paused'] and window.state['simulation_time_s']>paused_time+.1)
    checks.append('pause freezes UE time; resume advances it')
    if not window.state['tracking']:
        click(window.tracking_button); wait(lambda:window.state['tracking'])
    click(window.tracking_button)
    wait(lambda:not window.state['tracking'])
    held=(window.state['yaw_deg'],window.state['pitch_deg'])
    QTest.qWait(700)
    assert max(abs(a-b) for a,b in zip(held,(window.state['yaw_deg'],window.state['pitch_deg'])))<.001
    click(window.tracking_button); wait(lambda:window.state['tracking'])
    checks.append('gimbal hold and tracking from UI')
    click(window.rotors_button)
    wait(lambda:not window.state['rotors_running'])
    click(window.rotors_button)
    wait(lambda:window.state['rotors_running'])
    checks.append('rotor controls')
    window.sensor.setCurrentIndex(1)
    window.sensor.activated.emit(1)
    wait(lambda:window.state['sensor_mode']=='infrared')
    window.palette.setCurrentIndex(1)
    window.palette.activated.emit(1)
    wait(lambda:window.state['palette']=='black_hot')
    click(window.capture_button)
    wait(lambda:window.last_image_path is not None)
    assert (window.image.source.width(),window.image.source.height())==(640,512)
    checks.append('IR black-hot native snapshot rendered in UI')
    window.sensor.setCurrentIndex(0)
    window.sensor.activated.emit(0)
    wait(lambda:window.state['sensor_mode']=='visible')
    previous=window.last_image_path
    click(window.capture_button)
    wait(lambda:window.last_image_path!=previous)
    assert (window.image.source.width(),window.image.source.height())==(1920,1080)
    checks.append('visible native snapshot rendered in UI')
    window.fov.setValue(30)
    window.command('camera.set_fov',{'fov_deg':30})
    wait(lambda:window.state['fov_deg']==30)
    window.command('camera.set_fov',{'fov_deg':25})
    wait(lambda:window.state['fov_deg']==25)
    checks.append('FOV control')

    # Exercise the actual C++ byte-stream parser separately from Qt UI polling.
    with socket.create_connection(('127.0.0.1',50051),timeout=5) as peer:
        stream=peer.makefile('rb')
        packet=encode_request('fragment','sim.ping')
        for offset in range(0,len(packet),7): peer.sendall(packet[offset:offset+7])
        peer.sendall(encode_request('bad-fov','camera.set_fov',{'fov_deg':999})+encode_request('unknown','does.not.exist'))
        messages=[json.loads(stream.readline()) for _ in range(3)]
        assert [m['request_id'] for m in messages]==['fragment','bad-fov','unknown']
        assert [m['status'] for m in messages]==['ok','error','error']
        stream.close()
    checks.append('UE fragmented/coalesced TCP messages and argument errors')

    click(window.disconnect_button)
    wait(lambda:not window.client.ready)
    assert not window.pause_button.isEnabled() and window.summary_values['sensor'][0].text()=='—'
    click(window.connect_button)
    wait(lambda:window.client.ready)
    checks.append('disconnect clears stale state; reconnect succeeds')

    # A connected peer that never responds must not freeze the event loop.
    dummy=QTcpServer()
    assert dummy.listen(QHostAddress.SpecialAddress.LocalHost,0)
    peers=[]
    dummy.newConnection.connect(lambda:peers.append(dummy.nextPendingConnection()))
    silent=UEClient(AppConfig(timeout_ms=1000))
    errors=[]
    silent.failed.connect(lambda command,message:errors.append((command,message)))
    count=len(heartbeats)
    silent.connect_to('127.0.0.1',dummy.serverPort())
    wait(lambda:bool(errors),3)
    assert not silent.ready and len(heartbeats)-count>10
    silent.disconnect_from()
    for peer in peers: peer.abort()
    dummy.close()
    checks.append('response timeout does not block GUI')

    window.sensor.setCurrentIndex(1); window.sensor.activated.emit(1)
    wait(lambda:window.state['sensor_mode']=='infrared')
    window.palette.setCurrentIndex(0); window.palette.activated.emit(0)
    wait(lambda:window.state['palette']=='white_hot')
    previous=window.last_image_path
    click(window.capture_button)
    wait(lambda:window.last_image_path!=previous)
    QTest.qWait(200)
    (ROOT/'runtime').mkdir(exist_ok=True)
    window.grab().save(str(ROOT/'runtime/desktop_preview.png'))
    report={'passed':True,'checks':checks,'heartbeats':len(heartbeats),
            'last_state':window.state,'last_image':str(window.last_image_path)}
    (ROOT/'runtime/desktop_live_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'passed':True,'checks':checks},ensure_ascii=False),flush=True)
finally:
    window.close()
    app.processEvents()
