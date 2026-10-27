import shutil
import subprocess
import threading
import time
from collections import deque

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QImage


class RTSPVideoClient(QObject):
    frame_received = Signal(QImage, float)
    state_changed = Signal(bool, str)
    _worker_state = Signal(int, bool, str)
    WIDTH = 960
    HEIGHT = 540
    FRAME_BYTES = WIDTH * HEIGHT * 3

    def __init__(self, parent=None, size=None):
        super().__init__(parent)
        if size is not None:
            self.WIDTH, self.HEIGHT = size
            self.FRAME_BYTES = self.WIDTH * self.HEIGHT * 3
        self.url = ''
        self.running = False
        self.last_frame = 0.0
        self._generation = 0
        self._process = None
        self._lock = threading.Lock()
        self._pending = None
        self._overwritten = 0
        self._displayed = 0
        self._started = time.monotonic()
        self._connected = False
        self._display = QTimer(self)
        self._display.setInterval(16)
        self._display.timeout.connect(self._present)
        self._worker_state.connect(self._accept_worker_state)

    def _accept_worker_state(self, generation, connected, text):
        if generation == self._generation and self.running:
            if not connected:
                self._connected = False
            self.state_changed.emit(connected, text)

    def statistics(self):
        with self._lock:
            return dict(overwritten=self._overwritten, pending=int(self._pending is not None),
                        display_fps=self._displayed/max(.001, time.monotonic()-self._started))

    def _present(self):
        with self._lock:
            pending, self._pending = self._pending, None
        if pending and self.running and pending[0] == self._generation:
            self._displayed += 1
            if not self._connected:
                self._connected = True
                self.state_changed.emit(True, '实时视频已连接')
            self.frame_received.emit(pending[1], pending[2])
        elif self._connected and time.monotonic()-self.last_frame > 2:
            self._connected = False
            self.state_changed.emit(False, '实时视频已过期，等待新帧…')


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
        with self._lock:
            self._pending = None
            self._overwritten = self._displayed = 0
            self._started = time.monotonic()
        self._connected = False
        self._display.start()
        threading.Thread(target=self._worker, args=(generation, url), daemon=True).start()

    def stop(self):
        self.running = False
        self._generation += 1
        self._display.stop()
        with self._lock:
            process = self._process
            self._pending = None
        self._connected = False
        if process and process.poll() is None:
            process.terminate()

    def _worker(self, generation, url):
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            self._worker_state.emit(generation, False, '未找到 FFmpeg，无法播放 RTSP')
            return
        while self.running and generation == self._generation:
            frame_times = deque(maxlen=60)
            process = None
            try:
                process = subprocess.Popen([
                    ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin',
                    '-analyzeduration', '0', '-probesize', '32', '-rtsp_transport', 'tcp',
                    '-fflags', 'nobuffer', '-flags', 'low_delay',
                    '-threads', '1', '-reorder_queue_size', '0', '-max_delay', '0', '-i', url, '-an',
                    '-filter_threads', '1',
                    '-vf', f'scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,'
                           f'pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                    # Rawvideo's default frame-threaded encoder buffers several frames.
                    '-fps_mode', 'passthrough', '-pix_fmt', 'rgb24', '-threads', '1',
                    '-f', 'rawvideo', 'pipe:1',
                ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                with self._lock:
                    if generation != self._generation or not self.running:
                        process.terminate()
                        return
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
                    frame_times.append(now)
                    while len(frame_times) > 2 and now-frame_times[0] > 1.5:
                        frame_times.popleft()
                    fps = (len(frame_times)-1)/max(.001, now-frame_times[0])
                    self.last_frame = now
                    image = QImage(bytes(frame), self.WIDTH, self.HEIGHT, self.WIDTH * 3,
                                   QImage.Format.Format_RGB888).copy()
                    with self._lock:
                        if generation == self._generation and self.running:
                            if self._pending is not None:
                                self._overwritten += 1
                            self._pending = (generation, image, fps)
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
                self._worker_state.emit(generation, False, '等待 RTSP 视频源…')
                time.sleep(1.2)
