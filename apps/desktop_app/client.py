import time
import uuid
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QAbstractSocket, QTcpSocket
from core.protocol import JsonLines, ProtocolError, encode_request
from core.models import validate_state

class UEClient(QObject):
    connection_changed = Signal(bool, str)
    state_received = Signal(dict)
    completed = Signal(str, dict)
    failed = Signal(str, str)
    latency_changed = Signal(float)
    request_completed = Signal(str, str, dict, dict)
    request_failed = Signal(str, str, dict, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.device_id="ptz-01"
        self.config = config
        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self._connected)
        self.socket.disconnected.connect(self._disconnected)
        self.socket.readyRead.connect(self._read)
        self.socket.errorOccurred.connect(self._error)
        self.lines = JsonLines()
        self.pending = {}
        self.request_payloads = {}
        self.ready = False
        self.request_counter = 0
        self.session = uuid.uuid4().hex[:8]
        self.poll = QTimer(self)
        self.poll.setInterval(config.poll_ms)
        self.poll.timeout.connect(self._poll)
        self.deadlines = QTimer(self)
        self.deadlines.setInterval(100)
        self.deadlines.timeout.connect(self._check_deadlines)
        self.deadlines.start()
        self.connect_deadline = None

    def connect_to(self, host, port):
        self.disconnect_from()
        self.lines = JsonLines()
        self.connect_deadline = time.monotonic()+self.config.timeout_ms/1000
        self.socket.connectToHost(host, port)
        self.connection_changed.emit(False, '正在连接 UE…')

    def disconnect_from(self):
        self.connect_deadline = None
        self.poll.stop()
        self.ready = False
        self._fail_pending('连接已断开，操作结果未确认')
        self.socket.abort()
        self.connection_changed.emit(False, '未连接')

    def request(self, command, payload=None):
        if self.socket.state() != QAbstractSocket.SocketState.ConnectedState:
            self.failed.emit(command, 'UE 未连接')
            return None
        if len(self.pending) >= 32 or self.socket.bytesToWrite() > 65536:
            self.failed.emit(command, '请求繁忙，请稍后重试')
            return None
        self.request_counter += 1
        request_id = f'{self.session}-{self.request_counter}'
        try:
            payload=dict(payload or {})
            payload.setdefault("device_id",self.device_id)
            packet = encode_request(request_id, command, payload)
        except ValueError as exc:
            self.failed.emit(command, str(exc))
            return None
        self.pending[request_id] = (command, time.monotonic())
        self.request_payloads[request_id] = (command, dict(payload))
        if self.socket.write(packet) < 0:
            self.pending.pop(request_id, None)
            self.request_payloads.pop(request_id, None)
            self.failed.emit(command, self.socket.errorString())
            return None
        return request_id

    def _fail_pending(self, message):
        items = list(self.request_payloads.items())
        self.pending.clear()
        self.request_payloads.clear()
        for ident, (command, payload) in items:
            self.request_failed.emit(ident, command, payload, message)

    def _connected(self):
        self.connect_deadline = None
        self.request('sim.ping')

    def _disconnected(self):
        was_ready = self.ready
        self.ready = False
        self.poll.stop()
        pending = list(self.pending.values())
        self._fail_pending('连接已断开，操作结果未确认')
        self.lines = JsonLines()
        self.connection_changed.emit(False, 'UE 连接已断开' if was_ready else '未连接')
        for command, _ in pending:
            if command != 'sim.get_state':
                self.failed.emit(command, '连接已断开，操作结果未确认')

    def _error(self, _):
        text = self.socket.errorString()
        self.connect_deadline = None
        self.ready = False
        self.poll.stop()
        self._fail_pending('连接失败，操作结果未确认')
        self.connection_changed.emit(False, f'连接失败：{text}')

    def _read(self):
        try:
            messages = self.lines.feed(bytes(self.socket.readAll()))
        except ProtocolError as exc:
            self.failed.emit('protocol', str(exc))
            self.disconnect_from()
            return
        for message in messages:
            item = self.pending.pop(message['request_id'], None)
            if item is None:
                continue
            command, sent = item
            _, submitted = self.request_payloads.pop(message['request_id'], (command, {}))
            self.latency_changed.emit((time.monotonic()-sent)*1000)
            if message['status'] == 'error':
                error = message.get('error', {})
                self.failed.emit(command, str(error.get('message', 'UE 拒绝了操作')))
                self.request_failed.emit(message['request_id'], command, submitted, str(error.get('message', 'UE 拒绝了操作')))
                if command == 'sim.ping':
                    self.disconnect_from()
                continue
            payload = message['payload']
            try:
                validate_state(payload)
            except ProtocolError as exc:
                self.failed.emit(command, str(exc))
                self.disconnect_from()
                continue
            if command == 'sim.ping':
                if payload.get('application') != 'WISEYE Studio':
                    self.failed.emit('sim.ping', '连接的服务不是 WISEYE Studio')
                    self.disconnect_from()
                    continue
                self.ready = True
                self.poll.start()
                self.connection_changed.emit(True, '已连接 UE')
            self.state_received.emit(payload)
            self.request_completed.emit(message['request_id'], command, submitted, payload)
            self.completed.emit(command, payload)

    def _poll(self):
        if self.ready and not any(command == 'sim.get_state' for command, _ in self.pending.values()):
            self.request('sim.get_state')

    def _check_deadlines(self):
        now = time.monotonic()
        if self.connect_deadline and now > self.connect_deadline:
            self.disconnect_from()
            self.connection_changed.emit(False, '连接超时，请确认 UE 已开始播放')
        expired = [(key, value) for key, value in self.pending.items()
                   if now-value[1] > self.config.timeout_ms/1000]
        if expired:
            for key, (command, _) in expired:
                self.pending.pop(key, None)
                _, payload = self.request_payloads.pop(key, (command, {}))
                self.request_failed.emit(key, command, payload, 'UE 响应超时，操作结果未确认')
                self.failed.emit(command, 'UE 响应超时，操作结果未确认')
            self.disconnect_from()
            self.connection_changed.emit(False, '响应超时，已断开')
