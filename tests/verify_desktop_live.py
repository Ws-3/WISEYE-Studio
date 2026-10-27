"""Run from the repo with: python -m tests.verify_desktop_live (UE PIE required)."""
import json
import socket
import time
from pathlib import Path
import apps.desktop_app.main  # Preload Windows system ICU before importing PySide6.
from PySide6.QtGui import QImage
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
    wait(lambda:window.air_client.ready,45)
    if window.air_state.get('flight_status') == 'ready':
        click(window.takeoff_button)
        wait(lambda:not window.air_state.get('command_active',True) and window.air_state.get('flight_status') != 'ready',30)
    checks.append('real UE handshake and state polling')
    assert window.state.get('available_sensors') == ['visible', 'infrared', 'lidar']
    window.switch_video_channel()
    wait(lambda:not window.image.source.isNull(),20)
    ch1_frame=window.image.source.cacheKey()
    window.video_channel.setCurrentIndex(1); window.switch_video_channel()
    wait(lambda:not window.image.source.isNull() and window.image.source.cacheKey()!=ch1_frame,20)
    checks.append('CH1 visible and CH2 infrared RTSP render in the unified viewer')
    # A narrow single-frame scan aimed at sky/tiny UAV can legitimately have no hits.
    # Use the known ground for the data/export checks rather than assuming a hit.
    window.client.request('gimbal.set_angles', {'yaw_deg': 0, 'pitch_deg': -10})
    window.video_channel.setCurrentIndex(2); window.switch_video_channel()
    wait(lambda:window.view_tabs.currentIndex()==1 and window.lidar.total_count>0,10)
    checks.append('LIDAR live point cloud renders in the unified viewer')
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
    window.sensor_settings.setCurrentIndex(1)
    window.client.request('sensor.set_active',{'sensor':'infrared'})
    wait(lambda:window.state['sensor_mode']=='infrared' and window.state['active_sensor']=='infrared')
    window.palette.setCurrentIndex(1)
    window.sensor_settings.submit('infrared')
    wait(lambda:window.state['palette']=='black_hot')
    click(window.capture_button)
    wait(lambda:window.last_image_path is not None)
    assert (QImage(str(window.last_image_path)).width(),QImage(str(window.last_image_path)).height())==(640,512)
    checks.append('IR black-hot native snapshot rendered in UI')
    window.sensor_settings.setCurrentIndex(0)
    window.client.request('sensor.set_active',{'sensor':'visible'})
    wait(lambda:window.state['sensor_mode']=='visible')
    previous=window.last_image_path
    click(window.capture_button)
    wait(lambda:window.last_image_path!=previous)
    assert (QImage(str(window.last_image_path)).width(),QImage(str(window.last_image_path)).height())==(1920,1080)
    checks.append('visible native snapshot rendered in UI')
    window.sensor_settings.setCurrentIndex(2)
    window.client.request('sensor.set_active',{'sensor':'lidar'})
    wait(lambda:window.state['active_sensor']=='lidar')
    window.client.request('gimbal.set_angles', {'yaw_deg': 0, 'pitch_deg': -10})
    wait(lambda:not window.state['tracking'] and window.state.get('lidar_hits',0)>0)
    previous_clouds=set((ROOT/'ue5/WISEYE/Saved/WISEYE').glob('**/*.ply'))
    click(window.capture_button)
    wait(lambda:window.capture_button.isEnabled() and
         bool(set((ROOT/'ue5/WISEYE/Saved/WISEYE').glob('**/*.ply'))-previous_clouds))
    window.sensor_settings.setCurrentIndex(0); window.client.request('sensor.set_active',{'sensor':'visible'})
    wait(lambda:window.state['active_sensor']=='visible')
    checks.append('independent active sensor selection and LIDAR PLY export')
    window.client.request('gimbal.set_tracking', {'enabled': True})
    window.drone_model.setCurrentIndex(1); window.drone_model.activated.emit(1)
    wait(lambda:window.state['drone_model']=='avata')
    window.drone_model.setCurrentIndex(0); window.drone_model.activated.emit(0)
    wait(lambda:window.state['drone_model']=='mavic3')
    checks.append('Mavic 3 and Avata model switching')
    window.flight.setCurrentIndex(1); window.flight.activated.emit(1)
    wait(lambda:window.air_state.get('flight_mode')=='manual' and not window.air_state.get('paused', True) and window.state.get('input_mode')=='drone' and not window.air_state.get('command_active',True) and not any(c=='flight.set_mode' for c,_ in window.air_client.pending.values()))
    before=window.air_state['position_ned_m'][:2]
    QTest.keyPress(window,Qt.Key.Key_W); QTest.qWait(800); QTest.keyRelease(window,Qt.Key.Key_W)
    wait(lambda:sum((a-b)**2 for a,b in zip(window.air_state['position_ned_m'][:2],before))>.01)
    window.flight.setCurrentIndex(0); window.flight.activated.emit(0)
    wait(lambda:window.air_state.get('flight_mode')=='auto')
    checks.append('desktop W key manual AirSim flight and release-to-hover')
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

    window.sensor_settings.setCurrentIndex(1); window.client.request('sensor.set_active',{'sensor':'infrared'})
    wait(lambda:window.state['sensor_mode']=='infrared' and window.state['active_sensor']=='infrared')
    window.palette.setCurrentIndex(0); window.sensor_settings.submit('infrared')
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
