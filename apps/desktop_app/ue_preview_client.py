"""Native-resolution preview from UE's bounded latest-JPEG cache.

RTSP remains the integration/recording output. The interactive workbench does
not round-trip its local frames through another H.264 encoder and decoder.
"""
import threading
import time
from collections import deque

from PySide6.QtGui import QImage

from apps.desktop_app.rtsp_client import RTSPVideoClient
from integrations.rtsp.rtsp_gateway import UEFrameClient


class UEPreviewClient(RTSPVideoClient):
    POLL_HZ = 20

    def __init__(self, parent=None, size=None):
        super().__init__(parent, size)
        self._source = None
        self._wake = threading.Event()

    def start_source(self, host, port, channel, device_id=None):
        # Include source identity in start's equality check. Property/control
        # selection must never silently retarget an existing preview.
        self.start((host, int(port), channel, device_id))

    def stop(self):
        self._wake.set()
        super().stop()
        with self._lock:
            source = self._source
        if source:
            source.close()

    def _worker(self, generation, endpoint):
        host, port, channel, device_id = endpoint
        source = UEFrameClient(host, port, channel, 60, device_id, timeout=1)
        wake = threading.Event()
        with self._lock:
            if generation != self._generation or not self.running:
                return
            self._source = source
            self._wake = wake
        times = deque(maxlen=60)
        previous = None
        try:
            while self.running and generation == self._generation:
                began = time.monotonic()
                try:
                    encoded = source.frame()
                    metadata = source.last_payload
                    identity = (metadata['frame_number'], metadata['simulation_time_s'])
                    if identity != previous:
                        if (metadata['width'], metadata['height']) != (self.WIDTH, self.HEIGHT):
                            raise ValueError('Unexpected native preview dimensions')
                        image = QImage.fromData(encoded, 'JPEG')
                        if image.isNull() or (image.width(), image.height()) != (self.WIDTH, self.HEIGHT):
                            raise ValueError('Invalid native preview image')
                        now = time.monotonic()
                        times.append(now)
                        while len(times) > 2 and now - times[0] > 1.5:
                            times.popleft()
                        fps = (len(times) - 1) / max(.001, now - times[0])
                        with self._lock:
                            if generation != self._generation or not self.running:
                                break
                            self.last_frame = now
                            if self._pending is not None:
                                self._overwritten += 1
                            self._pending = (generation, image, fps)
                        previous = identity
                except (OSError, ValueError, RuntimeError, KeyError):
                    source.close()
                    previous = None
                    with self._lock:
                        if generation != self._generation or not self.running:
                            break
                        self._pending = None
                    self._worker_state.emit(generation, False, '等待 UE 最新画面…')
                    wake.wait(.25)
                wake.wait(max(0, 1 / self.POLL_HZ - (time.monotonic() - began)))
        finally:
            source.close()
            with self._lock:
                if self._source is source:
                    self._source = None
