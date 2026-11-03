"""Reference IR acceptance against real UE frames; writes evidence, restores controls.

Requires the new editor/runtime and an already connected AirSim flight worker.
Use an isolated test data directory. --flight performs one takeoff/land cycle.
"""
import argparse
import base64
import json
from pathlib import Path
import socket
import time

import cv2
import numpy as np


KEYS = ('enabled', 'fov_deg', 'palette', 'noise', 'thermal_profile', 'blur_px',
        'contrast', 'background_detail', 'agc_enabled', 'agc_response_s', 'sampling_scale')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='ptz-02')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--flight', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    def rpc(command, payload=None, port=50051, ok=True):
        payload = {'device_id':args.device, **(payload or {})} if port == 50051 else payload or {}
        with socket.create_connection(('127.0.0.1', port), 5) as peer:
            peer.settimeout(15)
            peer.sendall((json.dumps(dict(version=1, request_id=str(time.time_ns()), command=command,
                                         payload=payload)) + '\n').encode())
            response = json.loads(peer.makefile('rb').readline(16 * 1024**2))
        if not ok:
            return response
        assert response['status'] == 'ok', response
        return response['payload']

    def state():
        return rpc('sim.get_state')

    def config(**changes):
        settings = dict(initial)
        settings.update(enabled=True, **changes)
        rpc('sensor.configure', dict(sensor='infrared', **settings))

    def frame(channel='CH2'):
        packet = rpc('camera.stream_frame', dict(channel=channel, quality=60))
        image = cv2.imdecode(np.frombuffer(base64.b64decode(packet['image_base64']), np.uint8), cv2.IMREAD_COLOR)
        assert image is not None
        return image, packet

    def capture(name, settle=1.5):
        time.sleep(settle)
        _, first = frame()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            image, packet = frame()
            if packet['frame_number'] >= first['frame_number'] + 3:
                break
            time.sleep(.1)
        else:
            raise TimeoutError('IR stopped producing fresh frames')
        assert image.shape == (512, 640, 3), image.shape
        assert np.ptp(image, axis=2).max() <= 2, 'IR is not grayscale'
        assert image.std() > 2, 'Blank/constant sensor frame'
        cv2.imencode('.png', image)[1].tofile(str(args.output / (name + '.png')))
        report['captures'][name] = dict(frame_number=packet['frame_number'],
                                       simulation_time_s=packet['simulation_time_s'],
                                       mean=float(image.mean()), std=float(image.std()),
                                       sensor=state()['sensors']['infrared'])
        return image

    def measure(name, seconds=8):
        before = state()
        started = time.monotonic()
        samples = []
        while time.monotonic() - started < seconds:
            current = state()
            ir = current['sensors']['infrared']
            samples.append((current['streams']['CH2']['cache_age_ms'], ir['readout_ms']))
            time.sleep(.15)
        after = state()
        duration = time.monotonic() - started
        report['performance'][name] = dict(samples=len(samples),
            ue_tick_hz=(after['tick_seq'] - before['tick_seq']) / duration,
            fresh_ir_hz=(after['streams']['CH2']['completed_frames'] - before['streams']['CH2']['completed_frames']) / duration,
            cache_age_ms_p50=float(np.percentile(np.array(samples)[:, 0], 50)),
            cache_age_ms_p95=float(np.percentile(np.array(samples)[:, 0], 95)),
            readout_ms_p50=float(np.percentile(np.array(samples)[:, 1], 50)) if name.startswith('reference') else None,
            readout_ms_p95=float(np.percentile(np.array(samples)[:, 1], 95)) if name.startswith('reference') else None)
        print(name, report['performance'][name], flush=True)

    original = state()
    assert original['sensors']['infrared'].get('reference_available'), 'New material/runtime required'
    initial = {key: original['sensors']['infrared'][key] for key in KEYS}
    drone = original['tracking_target']
    report = dict(passed=False, scene=original['scene_id'], device=args.device, run_id=original['run_id'],
                  captures={}, performance={}, limitations='Short editor test; cache age is not sensor-to-display latency; FOV changes are angular-size tests, not range sweeps; normalized proxy is not radiometric calibration.')
    airborne = False
    try:
        rpc('gimbal.set_tracking', dict(enabled=True))
        config(thermal_profile='legacy', noise=0, palette='white_hot', fov_deg=25)
        legacy = capture('legacy')
        measure('legacy')
        config(thermal_profile='enhanced', noise=0, palette='white_hot', fov_deg=25)
        enhanced = capture('enhanced')
        config(thermal_profile='reference', noise=0, palette='white_hot', fov_deg=25,
               agc_enabled=True, agc_response_s=1, sampling_scale=1)
        reference = capture('reference', settle=4)
        measure('reference_1x')
        config(thermal_profile='reference', noise=0, palette='black_hot', fov_deg=25,
               agc_enabled=True, agc_response_s=1, sampling_scale=1)
        black = capture('reference_black_hot', settle=4)
        error = float(np.abs(reference.astype(float) + black.astype(float) - 255).mean())
        assert error < 12, ('Polarity mismatch', error)
        report['polarity_mean_error'] = error
        config(thermal_profile='reference', noise=0, palette='white_hot', fov_deg=25,
               agc_enabled=True, agc_response_s=1, sampling_scale=2)
        capture('reference_2x', settle=4)
        measure('reference_2x')
        for field in [dict(agc_enabled=1), dict(agc_response_s=0), dict(agc_response_s=11),
                      dict(sampling_scale=1.5), dict(sampling_scale=3)]:
            before = {key: state()['sensors']['infrared'][key] for key in KEYS}
            rejected = rpc('sensor.configure', {'sensor':'infrared', **before, **field}, ok=False)
            assert rejected['status'] != 'ok', rejected
            assert {key: state()['sensors']['infrared'][key] for key in KEYS} == before
        report['invalid_updates_rejected'] = 5
        config(thermal_profile='reference', noise=0, palette='white_hot', fov_deg=25,
               agc_enabled=False, sampling_scale=1)
        capture('reference_fixed_gain')
        readout = state()['sensors']['infrared']
        assert readout['agc_low'] == 0 and readout['agc_high'] == 1, readout
        config(thermal_profile='reference', noise=.008, palette='white_hot', fov_deg=25,
               agc_enabled=True, agc_response_s=1, sampling_scale=1)
        capture('reference_noise')
        for fov in (8, 25, 80):
            config(thermal_profile='reference', noise=.008, palette='white_hot', fov_deg=fov,
                   agc_enabled=True, agc_response_s=1, sampling_scale=1)
            capture(f'angular_fov_{fov}', settle=4)
        visible, _ = frame('CH1')
        assert visible.shape == (1080, 1920, 3)
        cv2.imencode('.jpg', visible)[1].tofile(str(args.output / 'visible.jpg'))
        config(thermal_profile='reference', noise=0, palette='white_hot', fov_deg=25,
               agc_enabled=True, agc_response_s=1, sampling_scale=1)
        current = capture('reference_export_source', settle=4)
        exported = rpc('camera.capture', dict(sensor='infrared'))
        saved = cv2.imread(exported['frame_path'])
        assert saved is not None and saved.shape == current.shape
        report['export_mean_difference'] = float(np.abs(saved.astype(float)-current.astype(float)).mean())
        assert report['export_mean_difference'] < 12, 'Display/export and stream disagree'
        if args.flight:
            def air(command='sim.get_state'):
                return rpc(command, dict(device_id=drone), port=50052)

            def wait_for(predicate, timeout=50):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if predicate():
                        return
                    time.sleep(.3)
                raise TimeoutError('Flight condition timed out')

            assert air()['flight_status'] == 'ready', 'Aircraft must initially be landed'
            cold = rpc('sim.get_state', dict(device_id=drone))['thermal_target']
            air('flight.takeoff'); airborne = True
            wait_for(lambda: not air()['command_active'])
            time.sleep(15)
            warm = rpc('sim.get_state', dict(device_id=drone))['thermal_target']
            capture('reference_hover_warm')
            assert warm['motor_warmth'] > cold['motor_warmth'] + .005, (cold, warm)
            air('flight.land')
            wait_for(lambda: air()['flight_status'] == 'ready' and max(air()['motor_rpm']) < 1)
            airborne = False
            landed = rpc('sim.get_state', dict(device_id=drone))['thermal_target']
            time.sleep(10)
            cooling = rpc('sim.get_state', dict(device_id=drone))['thermal_target']
            assert cooling['motor_warmth'] < landed['motor_warmth'], (landed, cooling)
            report['heat_cycle'] = dict(cold=cold, hover=warm, landed=landed, cooled=cooling)
        tiles = []
        for label, image in [('LEGACY', legacy), ('ENHANCED', enhanced), ('REFERENCE / AGC / 1x', reference)]:
            tile = cv2.copyMakeBorder(image, 36, 0, 0, 0, cv2.BORDER_CONSTANT, value=(25, 25, 25))
            cv2.putText(tile, label, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, .6, (225, 225, 225), 1, cv2.LINE_AA)
            tiles.append(tile)
        cv2.imencode('.png', np.hstack(tiles))[1].tofile(str(args.output / 'comparison.png'))
        report['passed'] = True
    finally:
        if airborne:
            rpc('flight.land', dict(device_id=drone), port=50052)
        rpc('sensor.configure', dict(sensor='infrared', **initial))
        rpc('gimbal.set_angles', dict(yaw_deg=original['yaw_deg'], pitch_deg=original['pitch_deg']))
        rpc('gimbal.set_tracking', dict(enabled=original['tracking']))
        report['restored'] = True
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(passed=report['passed'], output=str(args.output)), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
