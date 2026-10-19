import shutil
import subprocess
import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage


class RTSPVideoClient(QObject):
    frame_received = Signal(QImage, float)
    state_changed = Signal(bool, str)
    WIDTH = 960
    HEIGHT = 540
    FRAME_BYTES = WIDTH * HEIGHT * 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = ''
        self.running = False
        self.last_frame = 0.0
        self._generation = 0
        self._process = None
        self._lock = threading.Lock()

    def start(self, url):
        if self.running and self.url == url:
            return
        self.stop()
        self.url = url
        self.running = True
        self.last_frame = 0.0
        self._generation += 1
        generation = self._generation
        self.state_changed.emit(False, '正在连接实时视频…')
        threading.Thread(target=self._worker, args=(generation,), daemon=True).start()

    def stop(self):
        self.running = False
        self._generation += 1
        with self._lock:
            process = self._process
        if process and process.poll() is None:
            process.terminate()

    def _worker(self, generation):
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            self.state_changed.emit(False, '未找到 FFmpeg，无法播放 RTSP')
            return
        while self.running and generation == self._generation:
            process = None
            try:
                process = subprocess.Popen([
                    ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin',
                    '-analyzeduration', '0', '-probesize', '32', '-rtsp_transport', 'tcp',
                    '-fflags', 'nobuffer', '-flags', 'low_delay', '-i', self.url, '-an',
                    '-vf', f'scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,'
                           f'pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                    '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1',
                ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                with self._lock:
                    self._process = process
                assert process.stdout is not None
                while self.running and generation == self._generation:
                    frame = bytearray()
                    while len(frame) < self.FRAME_BYTES:
                        chunk = process.stdout.read(self.FRAME_BYTES - len(frame))
                        if not chunk:
                            break
                        frame.extend(chunk)
                    if len(frame) != self.FRAME_BYTES:
                        break
                    if not self.running or generation != self._generation:
                        break
                    now = time.monotonic()
                    fps = 0.0 if not self.last_frame else 1.0 / max(.001, now - self.last_frame)
                    self.last_frame = now
                    image = QImage(bytes(frame), self.WIDTH, self.HEIGHT, self.WIDTH * 3,
                                   QImage.Format.Format_RGB888).copy()
                    self.frame_received.emit(image, fps)
                    self.state_changed.emit(True, '实时视频已连接')
            except OSError:
                pass
            finally:
                with self._lock:
                    if self._process is process:
                        self._process = None
                if process:
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
            if self.running and generation == self._generation:
                self.state_changed.emit(False, '等待 RTSP 视频源…')
                time.sleep(1.2)
