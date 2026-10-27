"""V2 single-drone acceptance against real UE, AirSim and both RTSP channels."""
import json
import math
import socket
import time
import apps.desktop_app.main
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from apps.desktop_app.main_window import MainWindow
from core.config import ROOT, AppConfig
from core.layouts import LayoutStore

app = QApplication([])
window = MainWindow(AppConfig.load())
window.show()
checks, samples = [], []
window.client.latency_changed.connect(samples.append)
report = dict(passed=False, checks=checks)


def wait(predicate, timeout=20):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(25)
    raise AssertionError(window.logs.toPlainText()[-2500:])


def request(command, payload=None):
    with socket.create_connection(('127.0.0.1',50051), timeout=5) as peer:
        peer.sendall((json.dumps(dict(version=1, request_id='workbench', command=command, payload=payload or {}))+'\n').encode())
        return json.loads(peer.makefile('rb').readline())


layout_path = LayoutStore(ROOT).directory/'original.json'
previous_layout = layout_path.read_bytes() if layout_path.exists() else None
layout_modified = False
try:
    window.connect_ue()
    wait(lambda:window.client.ready and window.air_client.ready, 60)
    assert window.pages.count() == 4 and window.inspectors.count() == 3
    assert window.air_state.get('flight_status') == 'ready', window.air_state
    QTest.qWait(2200)
    assert window.air_state['flight_status'] == 'ready' and not window.air_state['command_active']
    checks.append('startup stays ready without arming, takeoff or automatic route')
    window.command('input.set_mode', {'mode':'observer'})
    wait(lambda:window.state.get('input_mode') == 'observer')

    window.observer_mode.setCurrentIndex(window.observer_mode.findData('free'))
    window.observer_mode.activated.emit(window.observer_mode.currentIndex())
    wait(lambda:window.state.get('observer_mode') == 'free')
    assert len(window.state['observer_position_cm']) == 3
    assert request('observer.set_mode', {'mode':'invalid'})['status'] == 'error'
    assert request('input.set_mode', {'mode':'invalid'})['status'] == 'error'
    checks.append('independent free camera created; invalid observer/control modes rejected')

    # New initial position must reach the actual AirSim robot, not just the visual.
    scene = window.scenes.currentData()
    original = LayoutStore(ROOT).load(scene)
    x = window.arrangement.coordinates['flight_origin_cm'][0]
    gx = window.arrangement.coordinates['gimbal_location_cm'][0]
    x.setValue(original['flight_origin_cm'][0]/100+1)
    gx.setValue(original['gimbal_location_cm'][0]/100+.25)
    window.arrangement.save()
    layout_modified = True
    run_id = window.state['run_id']
    window.switch_scene()
    wait(lambda:window.state.get('run_id') not in (None,run_id) and window.air_client.ready and window.air_state.get('flight_status') == 'ready' and window.air_state.get('run_id') == window.state.get('run_id'), 100)
    wait(lambda:abs(window.air_state['position_ned_m'][0]-(original['flight_origin_cm'][0]/100+1)) < .05, 40)
    assert abs(window.state['gimbal_position_cm'][0]-(original['gimbal_location_cm'][0]+25)) < .1
    checks.append('saved layout survives travel and sets actual AirSim origin plus gimbal mount')
    if previous_layout is None:
        layout_path.unlink()
    else:
        layout_path.write_bytes(previous_layout)
    layout_modified = False
    run_id = window.state['run_id']
    window.switch_scene()
    wait(lambda:window.state.get('run_id') not in (None,run_id) and window.air_client.ready and window.air_state.get('flight_status') == 'ready' and window.air_state.get('run_id') == window.state.get('run_id'), 100)
    window.arrangement.load()

    window.video_channel.setCurrentIndex(window.video_channel.findData('BOTH'))
    window.switch_video_channel()
    wait(lambda:not window.dual_visible.source.isNull() and not window.dual_infrared.source.isNull(), 30)
    QTest.qWait(2500)
    baseline = window.state['streams']
    t0 = time.monotonic()
    QTest.qWait(8000)
    elapsed = time.monotonic()-t0
    report['dual_preview_completed_new_fps'] = {key:(window.state['streams'][key]['completed_frames']-baseline[key]['completed_frames'])/elapsed for key in ('CH1','CH2')}
    before = window.video_client.statistics()['overwritten']
    time.sleep(.7)  # Deliberately stall the GUI while real FFmpeg workers continue.
    pending = window.video_client.statistics()
    assert pending['pending'] <= 1 and pending['overwritten'] > before, pending
    app.processEvents()
    checks.append('both live sensors render; GUI stall replaces old frames with a single pending frame')

    window.pages.setCurrentIndex(1)
    window.grab().save(str(ROOT/'docs/evidence/workbench_v2_20261019.png'))
    window.lidar_parameters['horizontal_fov_deg'].setValue(24)
    window.lidar_parameters['vertical_fov_deg'].setFocus()
    QTest.qWait(1100)
    assert window.lidar_parameters['horizontal_fov_deg'].value() == 24
    window.command('sensor.lidar.set_parameters', dict(horizontal_fov_deg=24, vertical_fov_deg=6, range_m=120, scan_rate_hz=5))
    wait(lambda:window.state.get('lidar_range_m') == 120 and window.state.get('lidar_scan_rate_hz') == 5)
    assert request('sensor.lidar.set_parameters', dict(horizontal_fov_deg=30, vertical_fov_deg=8, range_m=-1, scan_rate_hz=10))['status'] == 'error'
    window.command('sensor.lidar.set_parameters', dict(horizontal_fov_deg=30, vertical_fov_deg=8, range_m=300, scan_rate_hz=10))
    wait(lambda:window.state.get('lidar_range_m') == 300)
    checks.append('lidar parameters applied and read back; invalid request rejected atomically')

    window.command('flight.takeoff')
    wait(lambda:window.air_state.get('flight_status') == 'active' and not window.air_state.get('command_active',True), 35)
    window.flight.setCurrentIndex(1)
    window.flight.activated.emit(1)
    wait(lambda:window.state.get('input_mode') == 'drone' and not window.air_state['paused'])
    window.setFocus()
    QTest.keyPress(window, Qt.Key.Key_W)
    wait(lambda:window.air_state.get('last_manual_input') == [1,0,0,0])
    window.input_mode.setCurrentIndex(0)
    window.input_mode.activated.emit(0)
    wait(lambda:window.air_state.get('last_manual_input') == [0,0,0,0] and window.state.get('input_mode') == 'observer')
    QTest.keyRelease(window, Qt.Key.Key_W)
    before = window.air_state['manual_command_count']
    window.setFocus()
    QTest.keyPress(window, Qt.Key.Key_W)
    QTest.qWait(450)
    QTest.keyRelease(window, Qt.Key.Key_W)
    assert window.air_state.get('last_manual_input') == [0,0,0,0]
    assert window.air_state['manual_command_count'] <= before+2
    checks.append('switch from held flight input clears motion; observer mode refuses flight hotkeys')

    window.command('flight.land')
    wait(lambda:window.air_state.get('flight_status') == 'ready' and not window.air_state.get('command_active',True), 45)
    checks.append('takeoff and land return the session to ground ready')
    report['ue_control_roundtrip_ms_p95'] = sorted(samples)[min(len(samples)-1,int(len(samples)*.95))]
    report['p95_scope'] = 'UE JSON control round trip; not end-to-end video latency'
    report['passed'] = True
finally:
    if layout_modified:
        if previous_layout is None:
            layout_path.unlink(missing_ok=True)
        else:
            layout_path.write_bytes(previous_layout)
    window.close()
    (ROOT/'runtime/workbench_live_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
