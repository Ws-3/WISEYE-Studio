"""Independent GT preview. python -m training_client.preview --host <simulator IP>"""
import argparse
import os
from pathlib import Path
import sys
import threading
import time

# Match the desktop's system ICU workaround without importing simulator code.
if sys.platform == 'win32':
    import ctypes
    _icu = ctypes.WinDLL(str(Path(os.environ['SystemRoot']) / 'System32/icuuc.dll'))

from PySide6.QtCore import Qt, QThread, Signal, QRectF, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QSpinBox, QComboBox, QCheckBox, QPushButton, QFileDialog)
from .client import Client, validate_packet, save_sample, save_pair
from .rates import Rates


def ensure_fonts():
    # Qt's offscreen Windows plugin may expose no installed fonts.
    if not QFontDatabase.families() and sys.platform == 'win32':
        QFontDatabase.addApplicationFont(str(Path(os.environ['SystemRoot'])/'Fonts/msyh.ttc'))


def render_packet(packet):
    ensure_fonts()
    image = QImage.fromData(validate_packet(packet), 'JPEG')
    if image.isNull() or image.width() != packet['width'] or image.height() != packet['height']:
        raise ValueError('Decoded image dimensions do not match GT')
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    return draw_gt(image,packet)


def draw_gt(image, packet):
    image=image.copy()
    painter = QPainter(image)
    painter.setFont(QFont('Microsoft YaHei UI', 9))
    try:
        for ignored, objects in ((False, packet['objects']), (True, packet['ignored_objects'])):
            painter.setPen(QPen(QColor('#ffb347' if ignored else '#36ff76'), 2))
            for obj in objects:
                x1, y1, x2, y2 = obj['bbox_xyxy']
                painter.drawRect(QRectF(x1, y1, x2-x1, y2-y1))
                text = f"{obj['target_id']} {obj['visible_fraction_in_frame']:.0%}"
                painter.drawText(int(x1), max(15, int(y1)-4), text)
    finally:
        painter.end()
    return image


class Receiver(QThread):
    frame = Signal(object)
    status = Signal(str)
    metrics = Signal(object)
    settings_applied = Signal(int)

    def __init__(self, client, policy, output, sensors=('visible','infrared'),display_fps=1,save_fps=1,recording=None):
        super().__init__()
        self.client, self.policy, self.output = client, policy, output
        self.sensors=tuple(sensors)
        self.stop_event = threading.Event()
        self.capture_gate = None
        self.rates=Rates(display_fps,save_fps,bool(output) if recording is None else recording,max_display=30 if getattr(client,'source_kind','gimbal')=='aerial' else 10)
        self.settings_lock=threading.Lock();self.settings_revision=0
        self.latest_only=False;self.latest_lock=threading.Lock();self.latest_bundle=None

    def take_frame(self):
        with self.latest_lock:
            bundle,self.latest_bundle=self.latest_bundle,None
            return bundle

    def update_settings(self,policy,output):
        with self.settings_lock:
            if self.policy==policy and self.output==output:return self.settings_revision
            self.policy=dict(policy);self.output=output;self.settings_revision+=1
            with self.latest_lock:self.latest_bundle=None
            return self.settings_revision

    def settings(self):
        with self.settings_lock:return self.settings_revision,dict(self.policy),self.output

    def run(self):
        configured = False;configured_revision=-1
        received=saved=0;previous_identity=None;last_new=time.monotonic()
        while not self.stop_event.is_set():
            if self.capture_gate is not None and not self.capture_gate.is_set():
                self.stop_event.wait(.1); continue
            started = time.monotonic()
            try:
                revision,policy,output=self.settings()
                if not configured or revision!=configured_revision:
                    if getattr(self.client,'source_kind','gimbal')!='aerial':self.client.configure(**policy)
                    configured = True;configured_revision=revision;self.settings_applied.emit(revision)
                started=time.monotonic()
                aerial=getattr(self.client,'source_kind','gimbal')=='aerial'
                if aerial:
                    from .aerial import acquire
                    bundle=acquire(self.client,self.sensors,self.stop_event)
                    identity=tuple((sensor,p['run_id'],p['frame_number'],p['simulation_time_s']) for sensor,p in sorted(bundle['samples'].items()))
                    if identity==previous_identity:
                        if time.monotonic()-last_new>3:raise ValueError('Aerial source is stale; waiting for a new captured frame')
                        self.stop_event.wait(.02);continue
                    previous_identity=identity;last_new=time.monotonic()
                elif len(self.sensors)==2:
                    bundle=self.client.sample_pair(self.stop_event)
                else:
                    self.client.sensor=self.sensors[0]
                    packet=self.client.sample(self.stop_event)
                    bundle=dict(samples={self.sensors[0]:packet})
                from .fusion import decode
                if aerial:
                    from .aerial import validate_raw
                    images={sensor:QImage.fromData(validate_raw(packet),'JPEG') for sensor,packet in bundle['samples'].items()}
                    if any(image.isNull() or (image.width(),image.height())!=(bundle['samples'][sensor]['width'],bundle['samples'][sensor]['height']) for sensor,image in images.items()):raise ValueError('Aerial JPEG dimensions mismatch')
                else:images={sensor:decode(packet) for sensor,packet in bundle['samples'].items()}
                if self.settings()[0]!=revision:continue  # Never save an old-policy frame to a new directory.
                received+=1;now=time.monotonic();display,save=self.rates.due(now,source_driven=self.latest_only);did_save=False
                if save and output:
                    if aerial:
                        from .aerial import save_raw
                        did_save=any([save_raw(p,output) for p in bundle['samples'].values()])
                    elif len(self.sensors)==2:
                        save_pair(bundle,output);did_save=all(p['training_eligible'] for p in bundle['samples'].values())
                    else:did_save=save_sample(packet,Path(output)/('IR' if self.sensors[0]=='infrared' else 'visible')) is not None
                    saved+=int(did_save)
                if display:
                    if self.latest_only:
                        with self.latest_lock:self.latest_bundle=dict(bundle,_images=images)
                    else:self.frame.emit(bundle)
                self.metrics.emit(dict(received=received,saved=saved,displayed=display,did_save=did_save,at=time.monotonic()))
            except InterruptedError:
                break
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
                configured = False
                self.status.emit(str(error))
            while not self.stop_event.is_set():
                remaining=self.rates.period()-time.monotonic()+started
                if remaining<=0:break
                self.stop_event.wait(min(.1,remaining))


from .view import Canvas


from .workbench import Window


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=50100)
    parser.add_argument('--device', default='ptz-01')
    parser.add_argument('--sensor', choices=['both', 'infrared', 'visible'], default='both')
    try:
        from core.runtime_paths import DATA_ROOT,PORTABLE
    except ModuleNotFoundError:
        DATA_ROOT,PORTABLE=Path.home()/'WISEYE-Training',False
    parser.add_argument('--output', type=Path, default=DATA_ROOT/'Training' if PORTABLE else Path.home() / 'WISEYE-Training')
    parser.add_argument('--count', type=int, default=0, help='Headless sample count; saves original, labels and GT preview')
    parser.add_argument('--connect', action='store_true', help='Connect immediately on opening the window')
    args = parser.parse_args()
    if args.count:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication(sys.argv[:1])
    if PORTABLE:
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(DATA_ROOT/'QtSettings'))
    app.setFont(QFont('Microsoft YaHei UI', 10))
    if args.count:
        from .fusion import blend_pair
        client = Client(args.host, args.port, args.device, args.sensor); client.configure()
        for index in range(args.count):
            started=time.monotonic()
            if args.sensor=='both':
                pair=client.sample_pair();name=save_pair(pair,args.output)
                folder=args.output/'preview';folder.mkdir(parents=True,exist_ok=True)
                for sensor,packet in pair['samples'].items():
                    render_packet(packet).save(str(folder/f'{name}_{sensor}.png'))
                blend_pair(pair).save(str(folder/f'{name}_fusion.png'))
            else:
                packet=client.sample();name=save_sample(packet,args.output/('IR' if args.sensor=='infrared' else 'visible'))
            print(f'{index+1}: saved {name}',flush=True)
            time.sleep(max(0,1-time.monotonic()+started))
        return
    window = Window(args)
    window.visible.setChecked(args.sensor in ('both','visible')); window.infrared.setChecked(args.sensor in ('both','infrared'))
    window.show()
    if args.connect:
        QTimer.singleShot(0, window.start)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
