"""Owned integration smoke test for an independently installed custom UE host."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--scene', default='custom')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--allow-city', action='store_true')
    parser.add_argument('--allow-flight', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    data = output / 'Data'
    shutil.copytree(args.project.parent / 'Config/WISEYE', data / 'ue5/WISEYE/Config/WISEYE')
    shutil.copytree(root / 'configs', data / 'configs')
    os.environ['WISEYE_DATA_DIR'] = str(data)
    os.environ['WISEYE_PREVIEW_PROJECT'] = str(args.project.resolve())
    from PySide6.QtCore import QCoreApplication
    from apps.desktop_app.runtime_manager import RuntimeManager
    from core.local_rpc import request
    app = QCoreApplication([])
    runtime = RuntimeManager()
    report = {'passed': False, 'scene': args.scene, 'phases': [], 'captures': {}}
    runtime.phase.connect(lambda phase, message: report['phases'].append([phase, message]))
    runtime.failed.connect(lambda message: report.update(failure=message))
    ready = []
    runtime.ready.connect(lambda: ready.append(True))
    scene = json.loads((data / 'ue5/WISEYE/Config/WISEYE/Scenes' / (args.scene + '.json')).read_text(encoding='utf-8-sig'))

    def wait(function, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.processEvents()
            if report.get('failure'):
                raise RuntimeError(report['failure'])
            try:
                result = function()
                if result:
                    return result
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(.2)
        raise TimeoutError('Custom host readiness/capture timed out')

    def rpc(port, command, payload=None):
        response = request(port, command, payload or {}, timeout=8)
        if response.get('status') != 'ok':
            raise ValueError(response)
        return response['payload']

    try:
        runtime.launch(scene)
        wait(lambda: ready, 600)
        native = rpc(50051, 'sim.get_state')
        flight = rpc(50052, 'sim.get_state')
        assert native['scene_id'] == args.scene
        assert native['run_id'] == flight['run_id']
        if not args.allow_city:
            assert native['population']['vehicles_supported'] is False
            assert native['population']['pedestrians_supported'] is False
        report['run_id'] = native['run_id']
        report['flight_status'] = flight.get('flight_status')
        for channel in ['CH1', 'CH2']:
            packet = wait(lambda: rpc(50051, 'camera.stream_frame', {'device_id': 'ptz-01', 'channel': channel}), 90)
            image = base64.b64decode(packet.pop('image_base64'))
            assert image[:2] == b'\xff\xd8'
            (output / (channel + '.jpg')).write_bytes(image)
            report['captures'][channel] = packet
        if args.allow_flight:
            def air(command='sim.get_state', **values):
                return rpc(50052, command, {'device_id': 'uav-01', **values})
            air('flight.takeoff')
            wait(lambda: air()['flight_status'] == 'active' and not air()['command_active'], 90)
            air('flight.set_mode', mode='manual')
            wait(lambda: not air()['command_active'], 45)
            initial = air()
            assert max(initial['motor_rpm']) > 100
            for _ in range(8):
                air('flight.set_input', forward=0, right=0, up=.3, yaw=0)
                app.processEvents();time.sleep(.12)
            air('flight.set_input', forward=0, right=0, up=0, yaw=0)
            air('flight.hover')
            wait(lambda: not air()['command_active'], 45)
            moved = air()
            assert initial['position_ned_m'][2] - moved['position_ned_m'][2] > .05
            air('flight.land')
            wait(lambda: air()['flight_status'] == 'ready' and not air()['command_active'], 90)
            wait(lambda: max(air()['motor_rpm']) < 1, 30)
            report['flight_test'] = {'hover': initial, 'moved': moved, 'landed': air()}
        report['passed'] = True
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        runtime.stop()
        deadline = time.monotonic() + 80
        while runtime.running and time.monotonic() < deadline:
            app.processEvents();time.sleep(.2)
        report['owned_processes_stopped'] = not runtime.running
        if runtime.running:
            report['passed'] = False
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
