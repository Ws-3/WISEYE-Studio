"""Real city RGB/IR samples through data gateway; restores sensor and gimbal state."""
import argparse
import json
from pathlib import Path
import time

from training_client.client import Client, RPCError, save_sample
from training_client.preview import render_packet, QApplication


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    direct = Client(port=50051)
    receiver = Client()
    original = direct.rpc('sim.get_state')
    report = dict(passed=False, run_id=original['run_id'], samples={})
    def configure(sensor, fov):
        values = original['sensors'][sensor]
        payload = dict(sensor=sensor, enabled=values['enabled'], fov_deg=fov)
        if sensor == 'infrared':
            payload.update(palette=values['palette'], noise=values['noise'])
        direct.rpc('sensor.configure', **payload)
    def capture(name, sensor='infrared'):
        receiver.sensor = sensor
        time.sleep(.6)
        packet = receiver.sample()
        image = render_packet(packet)
        if not image.save(str(args.output/(name+'.png'))):
            raise OSError('Cannot save evidence')
        save_sample(packet, args.output/'dataset')
        report['samples'][name] = {k:v for k,v in packet.items() if k != 'image_base64'}
        print(name, json.dumps(packet['objects']), 'ignored', len(packet['ignored_objects']), flush=True)
        return packet
    try:
        receiver.configure()
        configure('infrared', 5); configure('visible', 5)
        direct.rpc('gimbal.set_tracking', enabled=True)
        time.sleep(2)
        centered = direct.rpc('sim.get_state')
        a = capture('infrared_target')
        b = capture('visible_target', 'visible')
        assert a['objects'] and b['objects'], 'Tracking target not visible'
        assert a['run_id'] == b['run_id'] == original['run_id']
        assert any(o['partially_occluded'] for o in a['objects']), 'Expected partial foreground obstruction in city view'
        receiver.sensor = 'infrared'
        receiver.configure(keep_partial_occlusion=False)
        assert Client(device='ptz-01').rpc('camera.gt_configure')['keep_partial_occlusion'] is True
        occluded_policy = capture('partial_occlusion_filtered')
        assert not occluded_policy['objects'] and occluded_policy['ignored_objects']
        assert not occluded_policy['negative_sample'] and not occluded_policy['training_eligible']
        receiver.configure()
        other = Client(device='ptz-01')
        other_state = other.rpc('sim.get_state')
        assert other_state['tracking'], 'Other gimbal must point at the occluded target'
        hidden = other.sample()
        assert hidden['negative_sample'] and not hidden['objects']
        report['samples']['other_gimbal_hidden'] = {k:v for k,v in hidden.items() if k != 'image_base64'}
        render_packet(hidden).save(str(args.output/'other_gimbal_hidden.png'))
        save_sample(hidden, args.output/'dataset')
        # Camera sweeps the target through the image boundary.
        receiver.sensor = 'infrared'
        clipped = None
        for offset in (2.3, 2.4, 2.5, 2.6):
            yaw = (centered['yaw_deg'] + offset + 180) % 360 - 180
            direct.rpc('gimbal.set_angles', yaw_deg=yaw, pitch_deg=centered['pitch_deg'])
            time.sleep(.3)
            candidate = capture('outside_'+str(offset).replace('.', '_'))
            if any(o['partially_outside'] for o in candidate['objects']):
                clipped = candidate; break
        assert clipped is not None, 'No partially clipped target found'
        receiver.configure(keep_partial_outside=False)
        filtered = capture('outside_filtered')
        assert not filtered['objects'] and filtered['ignored_objects'] and not filtered['training_eligible']
        receiver.configure()
        # Look away: a genuine empty label file must be committed.
        direct.rpc('gimbal.set_angles', yaw_deg=0, pitch_deg=25)
        time.sleep(.4)
        empty = capture('negative')
        assert empty['negative_sample'] and empty['training_eligible'] and not empty['objects']
        # Failure/disabled is distinct from a valid negative.
        direct.rpc('sensor.set_enabled', sensor='infrared', enabled=False)
        try:
            receiver.sample()
            raise AssertionError('Disabled sensor returned a sample')
        except RPCError as error:
            assert error.code == 'sensor_disabled'
        direct.rpc('sensor.set_enabled', sensor='infrared', enabled=True)
        # Invalid policy must be rejected atomically.
        try:
            receiver.rpc('camera.gt_configure', keep_partial_outside=False, min_visible_pixels=0)
            raise AssertionError('Invalid policy accepted')
        except RPCError as error:
            assert error.code == 'invalid_argument'
        actual = receiver.rpc('camera.gt_configure')
        assert actual['keep_partial_outside'] is True
        # Flight command must never pass through the data gateway.
        try:
            receiver.rpc('flight.takeoff')
            raise AssertionError('Gateway accepted flight control')
        except RPCError as error:
            assert error.code == 'gateway_error'
        before = direct.rpc('sim.get_state'); start = time.monotonic(); time.sleep(3)
        after = direct.rpc('sim.get_state'); duration = time.monotonic()-start
        baseline = dict(tick_hz=(after['tick_seq']-before['tick_seq'])/duration,
                        ir_hz=(after['streams']['CH2']['completed_frames']-before['streams']['CH2']['completed_frames'])/duration)
        before = after; start = time.monotonic()
        for _ in range(3):
            began = time.monotonic(); receiver.sample(); time.sleep(max(0, 1-time.monotonic()+began))
        after = direct.rpc('sim.get_state'); duration = time.monotonic()-start
        report['performance_observational'] = dict(baseline=baseline, sampling_1hz=dict(
            tick_hz=(after['tick_seq']-before['tick_seq'])/duration,
            ir_hz=(after['streams']['CH2']['completed_frames']-before['streams']['CH2']['completed_frames'])/duration))
        report['passed'] = True
    finally:
        for sensor in ('visible', 'infrared'):
            configure(sensor, original['sensors'][sensor]['fov_deg'])
        receiver.configure()
        if original['tracking']:
            direct.rpc('gimbal.set_tracking', enabled=True)
        else:
            direct.rpc('gimbal.set_angles', yaw_deg=original['yaw_deg'], pitch_deg=original['pitch_deg'])
        (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
