"""Exercise the real receiver thread and GUI against the running local gateway."""
import argparse
from pathlib import Path
import sys

from training_client.preview import QApplication, Window, QTimer
from training_client.client import Client


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    direct = Client(port=50051)
    state = direct.rpc('sim.get_state')
    def fov(sensor,value):
        original=state['sensors'][sensor]
        payload=dict(sensor=sensor,enabled=original['enabled'],fov_deg=value)
        if sensor=='infrared':payload.update(palette=original['palette'],noise=original['noise'])
        direct.rpc('sensor.configure',**payload)
    fov('visible',5);fov('infrared',5)
    direct.rpc('gimbal.set_tracking', enabled=True)
    window = Window(argparse.Namespace(host='127.0.0.1', port=50100, device='ptz-01', sensor='infrared', output=args.output/'dataset'))
    window.record.setChecked(True); window.show(); window.start()
    result = {'passed':False}
    def received(pair):
        if not pair['samples']['infrared']['objects']:
            return
        def capture():
            assert all(not tile.canvas.image.isNull() for tile in window.tiles.values())
            assert window.grab().save(str(args.output/'training-preview.png'))
            result['passed'] = True
            window.close(); app.quit()
        QTimer.singleShot(150, capture)
    def check_frame():
        if window.latest and not result['passed']:received(window.latest)
    checker=QTimer();checker.timeout.connect(check_frame);checker.start(250)
    def timeout():
        print(window.state.text(), flush=True); window.close(); app.quit()
    QTimer.singleShot(18000, timeout)
    app.exec()
    for sensor in ('visible','infrared'):fov(sensor,state['sensors'][sensor]['fov_deg'])
    if not state['tracking']:
        direct.rpc('gimbal.set_angles', yaw_deg=state['yaw_deg'], pitch_deg=state['pitch_deg'])
    assert result['passed'], 'GUI did not receive a paired frame'
    print('GUI receiver, GT drawing, sample save and clean thread exit passed', flush=True)


if __name__ == '__main__':
    main()
