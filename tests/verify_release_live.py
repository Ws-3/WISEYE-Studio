"""Exercise staged Game and frozen workers using a disposable configuration root."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time

parser = argparse.ArgumentParser()
parser.add_argument('--release', type=Path, required=True)
parser.add_argument('--scene', choices=['original', 'test_range', 'city'], default='original')
parser.add_argument('--allow-flight', action='store_true')
parser.add_argument('--unicode-paths', action='store_true')
args = parser.parse_args()
release = args.release.resolve()
repository = Path(__file__).resolve().parents[1]
test_root = repository / 'builds/live-tests' / f'{args.scene}-{time.time_ns()}'
if args.unicode_paths:
    test_root = test_root / '用户数据 测试'
test_root.mkdir(parents=True)
os.environ['WISEYE_RELEASE_ROOT'] = str(release)
os.environ['WISEYE_DATA_DIR'] = str(test_root / 'Data')
os.environ['PATH'] = os.environ['SystemRoot'] + r'\System32;' + os.environ['SystemRoot']

import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from apps.desktop_app.main_window import MainWindow
from apps.desktop_app.runtime_manager import request
from core.config import AppConfig
from integrations.gimbal_client import GimbalClient

app = QApplication([])
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(test_root / 'QtSettings'))
window = MainWindow(AppConfig.load())
window.resize(1600, 950)
window.show()
report = dict(passed=False, release=str(release), scene=args.scene, checks=[], test_root=str(test_root))
airborne = False
saved_gimbal = None


def pump(seconds=.1):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)


def wait(predicate, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pump(.1)
        try:
            if predicate():
                return
        except (OSError, ValueError):
            pass
        manager = getattr(window, 'runtime_manager', None)
        if manager and not manager.running and not report.get('passed'):
            raise RuntimeError('Packaged runtime exited during verification; see Data/logs')
    raise TimeoutError('Release condition timed out; see disposable Data/logs')


def rpc(command='sim.get_state', payload=None, port=50051):
    reply = request(port, command, payload)
    assert reply['status'] == 'ok', reply
    return reply['payload']


def air(command='sim.get_state', **payload):
    return rpc(command, dict(payload, device_id='uav-01'), 50052)


try:
    index = next(i for i in range(window.scenes.count()) if window.scenes.itemData(i)['id'] == args.scene)
    window.scenes.setCurrentIndex(index)
    window.launch_ue()
    wait(lambda: window.client.ready and window.air_client.ready, 300)
    state = rpc()
    ground = air()
    assert state['scene_id'] == args.scene and state['run_id'] == ground['run_id']
    assert state['dynamics_connected'] and ground['flight_status'] == 'ready'
    report.update(initial=state, ground=ground)
    report['checks'].append('Game and frozen flight worker ready with matching run ID')
    expected = {'ptz-01/visible': (1920, 1080), 'ptz-01/infrared': (640, 512), 'scene/observer': (960, 540)}
    wait(lambda: all(k in window.gallery.frames for k in expected), 90)
    for key, shape in expected.items():
        frame = window.gallery.frames[key]
        assert (frame.width(), frame.height()) == shape, (key, frame.size())
    report['frames'] = {k: [window.gallery.frames[k].width(), window.gallery.frames[k].height()] for k in expected}
    report['checks'].append('Native resolution visible, infrared and observer previews')
    sdk = GimbalClient(timeout=6)
    saved_gimbal = sdk.state()
    sdk.take_control()
    sdk.set_angles(0, 0)
    before = sdk.state()['yaw_deg']
    for _ in range(6):
        sdk.set_velocity(15, 0)
        pump(.1)
    sdk.stop()
    after = sdk.state()['yaw_deg']
    assert after - before > 3, (before, after)
    report['checks'].append('Gimbal velocity control changes actual angle')
    cloud = rpc('sensor.lidar.get_points', {'device_id': 'ptz-01'})
    assert cloud.get('lidar_points_m'), cloud
    report['lidar_count'] = len(cloud['lidar_points_m'])
    report['checks'].append('Nonempty LIDAR points')
    if args.allow_flight:
        airborne = True
        air('flight.takeoff')
        wait(lambda: air()['flight_status'] == 'active' and not air()['command_active'], 60)
        air('flight.set_mode', mode='manual')
        wait(lambda: not air()['command_active'], 45)
        pump(1)
        hover = air()
        assert max(hover['motor_rpm']) > 100
        for _ in range(6):
            air('flight.set_input', forward=0, right=0, up=.3, yaw=0)
            pump(.12)
        air('flight.set_input', forward=0, right=0, up=0, yaw=0)
        air('flight.hover')
        wait(lambda: not air()['command_active'], 45)
        pump(1)
        moved = air()
        assert hover['position_ned_m'][2] - moved['position_ned_m'][2] > .05
        air('flight.land')
        wait(lambda: air()['flight_status'] == 'ready' and not air()['command_active'], 75)
        wait(lambda: max(air()['motor_rpm']) < 1, 20)
        airborne = False
        report.update(hover=hover, moved=moved, landed=air())
        report['checks'].append('Real takeoff, rotor telemetry, manual ascent, landing and stopped motors')
    first = rpc()
    pump(10)
    last = rpc()
    assert last['run_id'] == first['run_id'] and last['tick_seq'] > first['tick_seq'] + 30
    report['tick_progress'] = [first['tick_seq'], last['tick_seq']]
    window.grab().save(str(test_root / 'workbench.png'))
    report['passed'] = True
finally:
    if airborne:
        try:
            air('flight.land')
            wait(lambda: air()['flight_status'] == 'ready', 75)
            airborne = False
        except Exception as error:
            report['landing_error'] = str(error)
    if saved_gimbal:
        try:
            sdk.stop()
            sdk.set_angles(saved_gimbal['yaw_deg'], saved_gimbal['pitch_deg'])
            if saved_gimbal['tracking']:
                sdk.track(saved_gimbal.get('tracking_target', 'uav-01'))
        except Exception as error:
            report['restore_error'] = str(error)
    manager = getattr(window, 'runtime_manager', None)
    if manager and not airborne:
        manager.stop()
        wait(lambda: not manager.running, 30)
    window.close()
    pump(.3)
    (test_root / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'checks': report['checks'], 'report': str(test_root / 'report.json')}, ensure_ascii=False), flush=True)
