import time
import uuid

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QAbstractSocket, QTcpSocket

from core.models import validate_airsim_state
from core.protocol import JsonLines, ProtocolError, encode_request


class AirSimClient(QObject):
    connection_changed = Signal(bool, str)
    state_received = Signal(dict)
    completed = Signal(str, dict)
    failed = Signal(str, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.device_id="uav-01"
        self.config = config
        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self._connected)
        self.socket.disconnected.connect(self._disconnected)
        self.socket.readyRead.connect(self._read)
        self.socket.errorOccurred.connect(self._error)
        self.lines = JsonLines()
        self.pending = {}
        self.latest_input = {}
        self.input_requests = {}
        self.ready = False
        self.request_counter = 0
        self.session = uuid.uuid4().hex[:8]
        self.host = config.host
        self.port = config.airsim_port
        self.poll = QTimer(self)
        self.poll.setInterval(config.poll_ms)
        self.poll.timeout.connect(self._poll)
        self.deadlines = QTimer(self)
        self.deadlines.setInterval(100)
        self.deadlines.timeout.connect(self._check_deadlines)
        self.deadlines.start()
        self.connect_deadline = None

    def connect_to(self, host=None):
        self.disconnect_from(quiet=True)
        self.host = host or self.config.host
        self.lines = JsonLines()
        self.connect_deadline = time.monotonic() + self.config.timeout_ms / 1000
        self.socket.connectToHost(self.host, self.port)
        self.connection_changed.emit(False, '正在连接 AirSim 飞控…')

    def disconnect_from(self, quiet=False):
        self.connect_deadline = None
        self.poll.stop()
        self.ready = False
        self.pending.clear()
        self.latest_input.clear();self.input_requests.clear()
        self.socket.abort()
        if not quiet:
            self.connection_changed.emit(False, 'AirSim 飞控未连接')

    def request(self, command, payload=None):
        payload=dict(payload or {})
        payload.setdefault('device_id',self.device_id)
        ident=payload['device_id']
        if command=='flight.set_input' and ident in self.input_requests:
            # One request on the wire per drone; key release replaces all
            # unsent movement, rather than joining a growing FIFO.
            self.latest_input[ident]=payload
            return self.input_requests[ident]
        if command in ('flight.land','flight.hover','flight.takeoff','flight.set_mode','sim.pause','sim.resume','sim.reset','route.start','route.stop','placement.apply'):
            self.latest_input.pop(ident,None)
        if self.socket.state() != QAbstractSocket.SocketState.ConnectedState:
            self.failed.emit(command, 'AirSim 飞控未连接')
            return None
        if len(self.pending) >= 32 or self.socket.bytesToWrite() > 65536:
            self.failed.emit(command, 'AirSim 飞控请求繁忙')
            return None
        self.request_counter += 1
        request_id = f'air-{self.session}-{self.request_counter}'
        try:
            payload=dict(payload or {})
            payload.setdefault("device_id",self.device_id)
            packet = encode_request(request_id, command, payload)
        except ValueError as exc:
            self.failed.emit(command, str(exc))
            return None
        self.pending[request_id] = (command, time.monotonic())
        if self.socket.write(packet) < 0:
            self.pending.pop(request_id, None)
            self.failed.emit(command, self.socket.errorString())
            return None
        if command=='flight.set_input':self.input_requests[ident]=request_id
        return request_id

    def _input_finished(self,request_id,success):
        ident=next((key for key,value in self.input_requests.items() if value==request_id),None)
        if ident is None:return
        self.input_requests.pop(ident,None)
        newest=self.latest_input.pop(ident,None)
        if success and newest is not None:self.request('flight.set_input',newest)

    def _connected(self):
        self.connect_deadline = None
        self.request('sim.ping')

    def _disconnected(self):
        was_ready = self.ready
        self.ready = False
        self.poll.stop()
        self.pending.clear()
        self.latest_input.clear();self.input_requests.clear()
        self.lines = JsonLines()
        self.connection_changed.emit(False, 'AirSim 飞控连接已断开' if was_ready else 'AirSim 飞控未连接')

    def _error(self, _):
        self.connect_deadline = None
        self.ready = False
        self.poll.stop()
        self.pending.clear()
        self.latest_input.clear();self.input_requests.clear()
        self.connection_changed.emit(False, f'AirSim 飞控连接失败：{self.socket.errorString()}')

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
            command, _ = item
            if message['status'] == 'error':
                self._input_finished(message['request_id'],False)
                self.failed.emit(command, str(message.get('error', {}).get('message', 'AirSim 拒绝了操作')))
                continue
            payload = message['payload']
            try:
                validate_airsim_state(payload)
            except ProtocolError as exc:
                self.failed.emit(command, str(exc))
                self.disconnect_from()
                return
            self._input_finished(message['request_id'],True)
            if payload.get('drone_id',self.device_id)!=self.device_id:
                if command=='placement.apply':self.completed.emit(command,payload)
                continue
            if command == 'sim.ping':
                self.ready = True
                self.poll.start()
                self.connection_changed.emit(True, 'AirSim 飞控已连接')
            self.state_received.emit(payload)
            self.completed.emit(command, payload)

    def _poll(self):
        if self.ready and not any(command == 'sim.get_state' for command, _ in self.pending.values()):
            self.request('sim.get_state')

    def _check_deadlines(self):
        now = time.monotonic()
        if self.connect_deadline and now > self.connect_deadline:
            self.disconnect_from()
        expired = [key for key, (_, sent) in self.pending.items()
                   if now - sent > self.config.timeout_ms / 1000]
        if expired:
            for key in expired:
                command, _ = self.pending.pop(key)
                self.failed.emit(command, 'AirSim 响应超时')
            self.disconnect_from()
