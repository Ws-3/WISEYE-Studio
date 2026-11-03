"""Independent latest-only preview; these frames never contain training GT."""
import base64
import math
import threading
import time
from collections import deque
from PySide6.QtGui import QImage
from .client import Client


class VideoPreview:
    def __init__(self, host, port, device, sensors, fps=20):
        self.host, self.port, self.device = host, port, device
        self.sensors = tuple(sensors)
        self.fps = fps
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.pending = {}  # At most one decoded image/error per subscribed sensor.
        self.threads = []

    def start(self):
        for sensor in self.sensors:
            thread = threading.Thread(target=self._run, args=(sensor,), daemon=True)
            self.threads.append(thread); thread.start()

    def take(self):
        with self.lock:
            result, self.pending = self.pending, {}
        return result

    def _run(self, sensor):
        client = Client(self.host, self.port, self.device)
        client.connect_timeout = client.response_timeout = .8
        channel = 'CH1' if sensor == 'visible' else 'CH2'
        previous = None; times = deque(maxlen=60)
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                packet = client.rpc('camera.stream_frame', channel=channel, quality=60)
                if packet.get('device_id') != self.device or packet.get('channel') != channel or packet.get('encoding') != 'jpeg':
                    raise ValueError('Preview source identity mismatch')
                width, height = packet['width'], packet['height']
                if type(width) is not int or type(height) is not int or not (0 < width <= 4096 and 0 < height <= 4096):
                    raise ValueError('Invalid preview dimensions')
                identity = packet['frame_number'], packet['simulation_time_s']
                if not all(type(v) in (float,int) and math.isfinite(v) for v in identity):
                    raise ValueError('Invalid preview timestamp')
                if identity != previous:
                    image = QImage.fromData(base64.b64decode(packet['image_base64'], validate=True), 'JPEG')
                    if image.isNull() or (image.width(), image.height()) != (width,height):
                        raise ValueError('Invalid preview JPEG')
                    now = time.monotonic(); times.append(now)
                    fps = (len(times)-1)/(times[-1]-times[0]) if len(times)>1 else 0
                    item = dict(image=image, frame_number=identity[0], simulation_time_s=identity[1], at=now, fps=fps)
                    with self.lock:self.pending[sensor] = item
                    previous = identity
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
                previous = None; times.clear()
                with self.lock:self.pending[sensor] = dict(error=str(error), at=time.monotonic())
                self.stop_event.wait(.15)
            self.stop_event.wait(max(0, 1/max(1,self.fps) - time.monotonic() + started))

    def stop(self):
        self.stop_event.set()

    def wait(self, timeout=2):
        deadline = time.monotonic()+timeout
        for thread in self.threads:thread.join(max(0,deadline-time.monotonic()))
        return all(not thread.is_alive() for thread in self.threads)
