import logging
import time
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QPointF, Qt, QSignalBlocker, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QFrame, QHBoxLayout,
    QVBoxLayout, QGridLayout, QSplitter, QTabWidget, QScrollArea)
from core.config import ROOT
from core.scenes import SceneStore
from apps.desktop_app.client import UEClient
from apps.desktop_app.airsim_client import AirSimClient
from apps.desktop_app.rtsp_client import RTSPVideoClient

STYLE = '''
QMainWindow, QWidget { background: #101722; color: #dce5f2; }
QWidget#sidebar { background: #0b111b; border-right: 1px solid #243144; }
QFrame#card { background: #192332; border: 1px solid #2b394d; border-radius: 10px; }
QLabel { background: transparent; }
QLabel#muted { color: #8c9eb6; }
QLabel#title { font-size: 22px; font-weight: 600; }
QLabel#value { font-size: 21px; font-weight: 600; color: #edf6ff; }
QLabel#badge { background: #263347; border-radius: 12px; padding: 6px 14px; }
QPushButton { background: #26364c; border: 1px solid #3a4c65; border-radius: 6px; padding: 8px 12px; }
QPushButton:hover { background: #354b66; border-color: #60a5c8; }
QPushButton:pressed { background: #193548; }
QPushButton:disabled { color: #64748b; border-color: #29374a; background: #1c293b; }
QPushButton#primary { background: #167e9b; border-color: #249cba; color: white; }
QPushButton#primary:hover { background: #2095b5; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #101a28; border: 1px solid #3a4c65; border-radius: 5px; padding: 6px; min-height: 22px; }
QComboBox QAbstractItemView { background: #172333; selection-background-color: #167e9b; }
QPlainTextEdit { background: #0d1622; border: 1px solid #2b394d; border-radius: 6px; color: #a8bad1; }
QSplitter::handle { background: #263347; height: 5px; }
QStatusBar { background: #0b111b; color: #8c9eb6; }
'''

class ImageView(QLabel):
    def __init__(self):
        super().__init__('等待 CH1 可见光实时画面')
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(430, 260)
        self.setStyleSheet('background:#080f18; color:#71869e; border:1px solid #2b394d; border-radius:8px;')
        self.source = QPixmap()

    def show_image(self, image):
        self.source = QPixmap.fromImage(image) if isinstance(image, QImage) else image
        self._fit()

    def _fit(self):
        if not self.source.isNull():
            self.setPixmap(self.source.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

class LidarView(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.total_count = 0
        self.setMinimumSize(430, 260)
        self.setToolTip('传感器局部坐标俯视图：前方朝上，左右对应云台视场')

    def set_points(self, points, total_count):
        self.points = [point for point in points if isinstance(point, list) and len(point) == 3]
        self.total_count = total_count
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#080f18'))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = 28
        area = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.setPen(QPen(QColor('#26384c'), 1))
        painter.drawRect(area)
        painter.drawLine(area.center().x(), area.top(), area.center().x(), area.bottom())
        painter.drawLine(area.left(), area.bottom(), area.right(), area.bottom())
        if not self.points:
            painter.setPen(QColor('#71869e'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '等待云台激光命中点')
            return
        max_forward = max(1.0, max(point[0] for point in self.points))
        max_side = max(1.0, max(abs(point[1]) for point in self.points))
        scale_x = area.height() / max_forward
        scale_y = area.width() / (2 * max_side)
        point_pen = QPen(QColor('#38d9ff'), 4)
        point_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(point_pen)
        for forward, side, _up in self.points:
            x = area.center().x() + side * scale_y
            y = area.bottom() - max(0.0, forward) * scale_x
            painter.drawPoint(QPointF(x, y))
        painter.setPen(QColor('#9db2c8'))
        painter.drawText(10, 18, f'实时点云 {self.total_count} 点 · 最远 {max_forward:.1f} m')

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle('WISEYE Studio · 智瞳控制台')
        self.resize(1320, 890)
        self.setMinimumSize(1080, 740)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(STYLE)
        self.client = UEClient(config, self)
        self.air_client = AirSimClient(config, self)
        self.video_client = RTSPVideoClient(self)
        self.config = config
        self.state = {}
        self.air_state = {}
        self.last_air_connect_attempt = 0.0
        self.control_widgets = []
        self.flight_widgets = []
        self.last_image_path = None
        self.switch_target = None
        self.switch_deadline = 0
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setInterval(1500)
        self.reconnect_timer.timeout.connect(self.reconnect_scene)
        self.lidar_poll = QTimer(self)
        self.lidar_poll.setInterval(200)
        self.lidar_poll.timeout.connect(self.poll_lidar)
        self.manual_timer = QTimer(self)
        self.manual_timer.setInterval(120)
        self.manual_timer.timeout.connect(self.send_manual_input)
        self.manual_input = (0.0, 0.0, 0.0, 0.0)
        self.manual_keys = set()
        self._build(config)
        self.client.connection_changed.connect(self.connection_changed)
        self.client.state_received.connect(self.apply_state)
        self.client.completed.connect(self.completed)
        self.client.failed.connect(self.failed)
        self.client.latency_changed.connect(lambda value: self.latency.setText(f'响应 {value:.0f} ms'))
        self.air_client.connection_changed.connect(self.air_connection_changed)
        self.air_client.state_received.connect(self.apply_air_state)
        self.air_client.completed.connect(self.air_completed)
        self.air_client.failed.connect(self.air_failed)
        self.video_client.frame_received.connect(self.video_frame)
        self.video_client.state_changed.connect(self.video_state_changed)
        self.connection_changed(False, '未连接')
        self.log('控制台已启动。请先启动 Project AirSim 仿真，再连接。')

    def _button(self, text, callback, primary=False, control=True):
        button = QPushButton(text)
        if primary:
            button.setObjectName('primary')
        button.clicked.connect(callback)
        if control:
            self.control_widgets.append(button)
        return button

    def _card(self):
        frame = QFrame()
        frame.setObjectName('card')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        return frame, layout

    def _label(self, text, name='muted'):
        label = QLabel(text)
        label.setObjectName(name)
        return label

    def _build(self, config):
        root = QWidget()
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        side = QWidget()
        side.setObjectName('sidebar')
        side.setFixedWidth(215)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(18, 24, 18, 20)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ROOT/'LOGO.jpg')).scaled(68, 68, Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation))
        side_layout.addWidget(logo)
        side_layout.addWidget(self._label('WISEYE', 'title'))
        side_layout.addWidget(self._label('智瞳 · 仿真与感知'))
        side_layout.addSpacing(24)
        section = QLabel('  仿真控制台')
        section.setStyleSheet('background:#183548; color:#7dd8f2; border-radius:6px; padding:12px 6px;')
        side_layout.addWidget(section)
        side_layout.addSpacing(18)
        side_layout.addWidget(self._label('UE 连接'))
        self.host = QLineEdit(config.host)
        self.host.setPlaceholderText('UE 地址')
        side_layout.addWidget(self.host)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(config.port)
        side_layout.addWidget(self.port)
        self.connect_button = self._button('连接 UE', self.connect_ue, True, False)
        self.disconnect_button = self._button('断开连接', self.client.disconnect_from, control=False)
        side_layout.addWidget(self.connect_button)
        side_layout.addWidget(self.disconnect_button)
        side_layout.addWidget(self._button('打开 UE 仿真', self.launch_ue, control=False))
        side_layout.addWidget(self._label('实验场景'))
        self.scenes = QComboBox()
        side_layout.addWidget(self.scenes)
        self.refresh_scenes()
        self.switch_button = self._button('切换到所选场景', self.switch_scene)
        side_layout.addWidget(self.switch_button)
        side_layout.addWidget(self._button('地图管理 / 导入', self.manage_scenes, control=False))
        self.active_scene = self._label('当前场景：未连接')
        self.active_scene.setWordWrap(True)
        side_layout.addWidget(self.active_scene)
        self.connection_detail = self._label('等待连接')
        self.connection_detail.setWordWrap(True)
        side_layout.addWidget(self.connection_detail)
        self.air_connection_detail = self._label('AirSim 飞控：等待连接')
        self.air_connection_detail.setWordWrap(True)
        side_layout.addWidget(self.air_connection_detail)
        side_layout.addStretch()
        note = self._label('可见光 1920 × 1080\n红外 640 × 512\n\n红外为模拟热成像')
        note.setWordWrap(True)
        side_layout.addWidget(note)
        row.addWidget(side)
        main = QWidget()
        content = QVBoxLayout(main)
        content.setContentsMargins(22, 20, 22, 14)
        content.setSpacing(14)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(self._label('仿真控制台', 'title'))
        titles.addWidget(self._label('无人机光电仿真 · 云台控制 · 双模态成像'))
        header.addLayout(titles)
        header.addStretch()
        self.badge = self._label('未连接', 'badge')
        header.addWidget(self.badge)
        content.addLayout(header)
        summary = QHBoxLayout()
        self.summary_values = {}
        for key, title in [('simulation', '仿真状态'), ('gimbal', '光电云台'), ('sensor', '成像模式')]:
            card, layout = self._card()
            layout.addWidget(self._label(title))
            value = self._label('—', 'value')
            layout.addWidget(value)
            detail = self._label('等待 UE 状态')
            layout.addWidget(detail)
            self.summary_values[key] = (value, detail)
            summary.addWidget(card)
        content.addLayout(summary)
        splitter = QSplitter(Qt.Orientation.Vertical)
        middle = QWidget()
        work = QHBoxLayout(middle)
        work.setContentsMargins(0, 0, 0, 0)
        work.setSpacing(14)
        view_card, view_layout = self._card()
        image_header = QHBoxLayout()
        image_header.addWidget(self._label('实时传感器画面'))
        image_header.addStretch()
        self.video_channel = QComboBox()
        self.video_channel.addItem('CH1 · 可见光', 'CH1')
        self.video_channel.addItem('CH2 · 红外', 'CH2')
        self.video_channel.addItem('LIDAR · 激光点云', 'LIDAR')
        self.video_channel.activated.connect(self.switch_video_channel)
        image_header.addWidget(self.video_channel)
        self.capture_button = self._button('保存工作传感器数据', self.capture_active_sensor)
        image_header.addWidget(self.capture_button)
        view_layout.addLayout(image_header)
        self.view_tabs = QTabWidget()
        self.image = ImageView()
        self.lidar = LidarView()
        self.view_tabs.addTab(self.image, '实时图像')
        self.view_tabs.addTab(self.lidar, '激光点云')
        self.view_tabs.currentChanged.connect(self.view_tab_changed)
        view_layout.addWidget(self.view_tabs, 1)
        self.image_caption = self._label('CH1 可见光 · 等待 RTSP 视频源')
        self.image_caption.setWordWrap(True)
        view_layout.addWidget(self.image_caption)
        work.addWidget(view_card, 1)
        controls, layout = self._card()
        controls.setMinimumWidth(290)
        layout.addWidget(self._label('仿真控制'))
        buttons = QHBoxLayout()
        self.pause_button = self._button('暂停', lambda: self.command('sim.pause'))
        self.resume_button = self._button('继续', lambda: self.command('sim.resume'))
        self.flight_widgets += [self.pause_button, self.resume_button]
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.resume_button)
        layout.addLayout(buttons)
        self.reset_button = self._button('复位航线', lambda: self.command('sim.reset'))
        self.flight_widgets.append(self.reset_button)
        layout.addWidget(self.reset_button)
        flight_actions = QHBoxLayout()
        self.takeoff_button = self._button('起飞', lambda: self.command('flight.takeoff'))
        self.hover_button = self._button('悬停', lambda: self.command('flight.hover'))
        self.land_button = self._button('降落', lambda: self.command('flight.land'))
        self.flight_widgets += [self.takeoff_button, self.hover_button, self.land_button]
        for button in (self.takeoff_button, self.hover_button, self.land_button):
            flight_actions.addWidget(button)
        layout.addLayout(flight_actions)
        self.flight = QComboBox()
        self.flight.addItem('自动航线', 'auto')
        self.flight.addItem('手动飞行（界面按键 / 键盘）', 'manual')
        self.flight.activated.connect(self.set_flight_mode)
        layout.addWidget(self.flight)
        self.control_widgets.append(self.flight)
        self.flight_widgets.append(self.flight)
        layout.addWidget(self._label('手动控制：先选择“手动飞行”，再按住按钮或键盘\nW/S 前后 · A/D 左右 · R/F 升降 · Q/E 转向'))
        manual = QGridLayout()
        manual_specs = [
            ('升', (0, 0, 1, 0), 0, 0), ('前', (1, 0, 0, 0), 0, 1), ('降', (0, 0, -1, 0), 0, 2),
            ('左', (0, -1, 0, 0), 1, 0), ('悬停', (0, 0, 0, 0), 1, 1), ('右', (0, 1, 0, 0), 1, 2),
            ('左转', (0, 0, 0, -1), 2, 0), ('后', (-1, 0, 0, 0), 2, 1), ('右转', (0, 0, 0, 1), 2, 2),
        ]
        for text, vector, row_index, column_index in manual_specs:
            button = QPushButton(text)
            button.pressed.connect(lambda value=vector: self.start_manual_input(value))
            button.released.connect(self.stop_manual_input)
            manual.addWidget(button, row_index, column_index)
            self.control_widgets.append(button)
            self.flight_widgets.append(button)
        layout.addLayout(manual)
        layout.addWidget(self._label('无人机型号'))
        self.drone_model = QComboBox()
        self.drone_model.addItem('DJI Mavic 3', 'mavic3')
        self.drone_model.addItem('DJI Avata', 'avata')
        self.drone_model.activated.connect(
            lambda _: self.command('drone.set_model', {'model': self.drone_model.currentData()}))
        layout.addWidget(self.drone_model)
        layout.addWidget(self._label('切换外观型号；飞行仍由同一套 AirSim 动力学控制'))
        self.control_widgets.append(self.drone_model)
        self.tracking_button = self._button('保持云台方向', lambda: self.command('gimbal.set_tracking', {'enabled': not self.state.get('tracking', True)}))
        self.rotors_button = self._button('停止旋翼', lambda: self.command('rotors.set_enabled', {'enabled': not self.state.get('rotors_running', True)}))
        layout.addWidget(self.tracking_button)
        layout.addWidget(self.rotors_button)
        layout.addWidget(self._label('光电云台工作传感器'))
        self.sensor = QComboBox()
        self.sensor.addItem('可见光 · 1920 × 1080', 'visible')
        self.sensor.addItem('红外 · 640 × 512', 'infrared')
        self.sensor.addItem('激光雷达 · 实时点云', 'lidar')
        self.sensor.activated.connect(
            lambda _: self.command('sensor.set_active', {'sensor': self.sensor.currentData()}))
        layout.addWidget(self.sensor)
        layout.addWidget(self._label('已接入：可见光、红外、激光雷达\n深度相机、事件相机和雷达将在设备接入后自动扩展'))
        self.palette = QComboBox()
        self.palette.addItem('白热', 'white_hot')
        self.palette.addItem('黑热', 'black_hot')
        self.palette.activated.connect(lambda _: self.command('camera.set_palette', {'palette': self.palette.currentData()}))
        layout.addWidget(self.palette)
        self.control_widgets += [self.sensor, self.palette]
        fov_row = QHBoxLayout()
        self.fov = QDoubleSpinBox()
        self.fov.setRange(5, 120)
        self.fov.setValue(25)
        self.fov.setSuffix(' °')
        self.fov.setDecimals(1)
        fov_row.addWidget(self.fov)
        fov_row.addWidget(self._button('设置视场', lambda: self.command('camera.set_fov', {'fov_deg': self.fov.value()})))
        self.control_widgets.append(self.fov)
        layout.addLayout(fov_row)
        self.angle_label = self._label('偏航 —  /  俯仰 —')
        self.position_label = self._label('无人机位置：—')
        self.position_label.setWordWrap(True)
        layout.addWidget(self.angle_label)
        layout.addWidget(self.position_label)
        layout.addStretch()
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setFrameShape(QFrame.Shape.NoFrame)
        control_scroll.setFixedWidth(320)
        control_scroll.setWidget(controls)
        work.addWidget(control_scroll)
        splitter.addWidget(middle)
        log_card, log_layout = self._card()
        log_header = QHBoxLayout()
        log_header.addWidget(self._label('操作日志'))
        log_header.addStretch()
        log_layout.addLayout(log_header)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(500)
        log_layout.addWidget(self.logs)
        splitter.addWidget(log_card)
        splitter.setSizes([560, 160])
        content.addWidget(splitter, 1)
        row.addWidget(main, 1)
        self.latency = QLabel('响应 —')
        self.statusBar().addPermanentWidget(self.latency)
        self.statusBar().showMessage('UE 独立运行，开始播放后即可连接控制台')

    def log(self, message):
        self.logs.appendPlainText(f'{datetime.now():%H:%M:%S}  {message}')
        logging.info(message)

    def connect_ue(self):
        host = self.host.text().strip()
        if not host:
            self.log('请填写 UE 地址。')
            return
        self.client.connect_to(host, self.port.value())
        self.air_client.connect_to(host)

    def launch_ue(self):
        from PySide6.QtCore import QProcess
        scene = self.scenes.currentData() or {}
        scene_id = scene.get('id', 'original')
        if scene_id in ('original', 'test_range'):
            arguments = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                         str(ROOT/'scripts/Start-ProjectAirSim.ps1'), '-SkipBuild', '-Scene', scene_id]
            message = '已请求启动 UE 与 AirSim；播放和飞行会自动开始。'
        else:
            arguments = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                         str(ROOT/'scripts/Start-WISEYE.ps1'), '-SkipBuild', '-Map',
                         scene.get('map', '/Game/WISEYE-test')]
            message = '该地图尚无 AirSim 配置，已打开 UE；加载后请点击播放。'
        started = QProcess.startDetached('powershell.exe', arguments, str(ROOT))
        self.log(message if started[0] else 'UE 启动失败，请检查引擎路径。')

    def connection_changed(self, connected, text):
        self.badge.setText('已连接' if connected else '未连接')
        self.badge.setStyleSheet('background:#174936; color:#89e1af; border-radius:12px; padding:6px 14px;' if connected else '')
        self.connection_detail.setText(text)
        connecting = self.client.connect_deadline is not None
        self.connect_button.setEnabled(not connected and not connecting)
        self.disconnect_button.setEnabled(connected or connecting)
        self.host.setEnabled(not connected and not connecting)
        self.port.setEnabled(not connected and not connecting)
        self.statusBar().showMessage(text)
        for widget in self.control_widgets:
            widget.setEnabled(connected)
        if self.switch_target:
            self.switch_button.setEnabled(False)
        if not connected:
            self.lidar_poll.stop()
            self.video_client.stop()
            self.active_scene.setText('当前场景：切换中' if self.switch_target else '当前场景：未连接')
            self.state = {}
            for value, detail in self.summary_values.values():
                value.setText('—')
                detail.setText('状态不可用')
            self.angle_label.setText('偏航 —  /  俯仰 —')
            self.position_label.setText('无人机位置：—')
            self.latency.setText('响应 —')
            if self.last_image_path:
                self.image_caption.setText('连接已断开 · 保留上次截图，非当前画面')
        elif not self.video_client.running:
            self.switch_video_channel()
        self.update_flight_controls()
        self.log(text)

    def air_connection_changed(self, connected, text):
        self.air_connection_detail.setText(text)
        if not connected:
            self.air_state = {}
        self.update_flight_controls()
        self.log(text)

    def command(self, command, payload=None):
        if not self.client.ready:
            self.log('请先连接 UE。')
            return
        is_airsim = self.state.get('flight_backend') == 'projectairsim'
        flight_command = command in ('sim.pause', 'sim.resume', 'sim.reset', 'flight.takeoff',
                                     'flight.hover', 'flight.land', 'flight.set_mode', 'flight.set_input')
        if is_airsim and flight_command:
            if not self.air_client.ready:
                self.log('AirSim 飞控尚未连接，请从 Start-ProjectAirSim 启动仿真。')
                return
            self.air_client.request(command, payload)
            if command in ('sim.pause', 'sim.resume', 'sim.reset', 'flight.set_mode'):
                self.client.request(command, payload)
        else:
            self.client.request(command, payload)
        if command in ('camera.capture', 'sensor.lidar.capture'):
            self.capture_button.setEnabled(False)

    def capture_active_sensor(self):
        sensor = self.state.get('active_sensor', self.state.get('sensor_mode', 'visible'))
        self.command('sensor.lidar.capture' if sensor == 'lidar' else 'camera.capture')

    def apply_state(self, state):
        self.state = state
        if not self.client.ready:
            return
        scene_id = state.get('scene_id', '旧版 UE 未提供场景信息')
        if (state.get('flight_backend') == 'projectairsim' and not self.air_client.ready
                and self.air_client.connect_deadline is None
                and time.monotonic() - self.last_air_connect_attempt >= 3.0):
            self.last_air_connect_attempt = time.monotonic()
            self.air_client.connect_to(self.host.text().strip())
        self.active_scene.setText('当前场景：' + scene_id)
        if self.switch_target and scene_id == self.switch_target:
            self.log('场景切换完成，已恢复 UE 连接：' + scene_id)
            self.switch_target = None
            self.reconnect_timer.stop()
            self.switch_button.setEnabled(True)
        value, detail = self.summary_values['simulation']
        paused = self.air_state.get('paused', state['paused']) if state.get('flight_backend') == 'projectairsim' else state['paused']
        mode = self.air_state.get('flight_mode', state['flight_mode']) if state.get('flight_backend') == 'projectairsim' else state['flight_mode']
        value.setText('已暂停' if paused else '运行中')
        backend = 'AirSim' if state.get('flight_backend') == 'projectairsim' else '运动学'
        detail.setText(f"{backend} · 航线时间 {state['simulation_time_s']:.1f} s · {'自动' if mode=='auto' else '手动'}")
        value, detail = self.summary_values['gimbal']
        value.setText('目标跟踪' if state['tracking'] else '方向保持')
        detail.setText(f"指向误差 {state['pointing_error_deg']:.3f}° · 真值指向")
        value, detail = self.summary_values['sensor']
        active_sensor = state.get('active_sensor', state['sensor_mode'])
        sensor_names = {'visible': '可见光', 'infrared': '红外', 'lidar': '激光雷达'}
        value.setText(sensor_names.get(active_sensor, active_sensor))
        if active_sensor == 'lidar':
            detail.setText(
                f"回波 {state.get('lidar_hits',0)}/{state.get('lidar_rays',0)} · 最近 {state.get('lidar_nearest_m',0):.1f} m")
        else:
            detail.setText(f"{state['width']} × {state['height']} · 激光 {state.get('lidar_hits',0)}/{state.get('lidar_rays',0)}")
        display_state = dict(state)
        display_state['flight_mode'] = mode
        display_state['active_sensor'] = active_sensor
        for combo, key in [(self.flight, 'flight_mode'), (self.sensor, 'active_sensor'), (self.palette, 'palette')]:
            blocker = QSignalBlocker(combo)
            combo.setCurrentIndex(combo.findData(display_state[key]))
            del blocker
        model = state.get('drone_model', 'mavic3')
        blocker = QSignalBlocker(self.drone_model)
        self.drone_model.setCurrentIndex(max(0, self.drone_model.findData(model)))
        del blocker
        if not self.fov.hasFocus():
            self.fov.setValue(state['fov_deg'])
        self.pause_button.setEnabled(not paused)
        self.resume_button.setEnabled(paused)
        self.palette.setEnabled(active_sensor == 'infrared')
        self.tracking_button.setText('保持云台方向' if state['tracking'] else '恢复目标跟踪')
        self.rotors_button.setText('停止旋翼' if state['rotors_running'] else '启动旋翼')
        self.angle_label.setText(f"偏航 {state['yaw_deg']:.1f}°  /  俯仰 {state['pitch_deg']:.1f}°")
        position = state['drone_position_cm']
        self.position_label.setText(f'无人机位置（m）\nX {position[0]/100:.2f} · Y {position[1]/100:.2f} · Z {position[2]/100:.2f}')
        if not self.lidar_poll.isActive():
            self.lidar_poll.start()
        self.update_flight_controls()

    def apply_air_state(self, state):
        self.air_state = state
        if self.state:
            self.apply_state(self.state)
        if state.get('last_error'):
            self.air_connection_detail.setText('AirSim 飞控：' + state['last_error'])

    def update_flight_controls(self):
        is_airsim = self.state.get('flight_backend') == 'projectairsim'
        available = self.client.ready and (not is_airsim or self.air_client.ready)
        mode = self.air_state.get('flight_mode', self.state.get('flight_mode'))
        paused = self.air_state.get('paused', self.state.get('paused', False))
        for widget in self.flight_widgets:
            widget.setEnabled(available)
        self.pause_button.setEnabled(available and not paused)
        self.resume_button.setEnabled(available and paused)
        for widget in self.flight_widgets:
            if widget not in (self.pause_button, self.resume_button, self.reset_button, self.flight,
                              self.takeoff_button, self.hover_button, self.land_button):
                widget.setEnabled(available and mode == 'manual' and not paused)

    def poll_lidar(self):
        if (self.client.ready and self.state.get('lidar_enabled', False)
                and not any(command == 'sensor.lidar.get_points'
                            for command, _ in self.client.pending.values())):
            self.client.request('sensor.lidar.get_points')

    def start_manual_input(self, vector):
        self.manual_input = tuple(float(value) for value in vector)
        self.send_manual_input()
        self.manual_timer.start()

    def set_flight_mode(self, _index=None):
        self.command('flight.set_mode', {'mode': self.flight.currentData()})
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _keyboard_manual_input(self):
        forward = float((Qt.Key.Key_W in self.manual_keys) - (Qt.Key.Key_S in self.manual_keys))
        right = float((Qt.Key.Key_D in self.manual_keys) - (Qt.Key.Key_A in self.manual_keys))
        up = float((Qt.Key.Key_R in self.manual_keys) - (Qt.Key.Key_F in self.manual_keys))
        yaw = float((Qt.Key.Key_E in self.manual_keys) - (Qt.Key.Key_Q in self.manual_keys))
        self.manual_input = (forward, right, up, yaw)
        self.send_manual_input()
        if self.manual_keys:
            self.manual_timer.start()
        else:
            self.manual_timer.stop()

    def keyPressEvent(self, event):
        manual_keys = {Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D,
                       Qt.Key.Key_R, Qt.Key.Key_F, Qt.Key.Key_Q, Qt.Key.Key_E}
        if event.key() in manual_keys and not event.isAutoRepeat():
            if self.air_client.ready and self.air_state.get('flight_mode') == 'manual':
                self.manual_keys.add(event.key())
                self._keyboard_manual_input()
                event.accept()
                return
            self.statusBar().showMessage('请先在飞行模式中选择“手动飞行”')
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() in self.manual_keys and not event.isAutoRepeat():
            self.manual_keys.discard(event.key())
            self._keyboard_manual_input()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def stop_manual_input(self):
        self.manual_timer.stop()
        self.manual_input = (0.0, 0.0, 0.0, 0.0)
        self.send_manual_input()

    def send_manual_input(self):
        if self.air_client.ready and self.air_state.get('flight_mode') == 'manual':
            forward, right, up, yaw = self.manual_input
            self.air_client.request('flight.set_input', {
                'forward': forward, 'right': right, 'up': up, 'yaw': yaw,
            })

    def switch_video_channel(self):
        channel = self.video_channel.currentData() or 'CH1'
        if channel == 'LIDAR':
            self.video_client.stop()
            blocker = QSignalBlocker(self.view_tabs)
            self.view_tabs.setCurrentIndex(1)
            del blocker
            count = self.state.get('lidar_hits', 0)
            self.image_caption.setText(f'LIDAR 激光点云 · 实时 · 当前 {count} 个回波点')
            return
        blocker = QSignalBlocker(self.view_tabs)
        self.view_tabs.setCurrentIndex(0)
        del blocker
        path = self.config.rtsp_visible_path if channel == 'CH1' else self.config.rtsp_infrared_path
        host = self.host.text().strip() or self.config.host
        self.video_client.start(f'rtsp://{host}:{self.config.rtsp_port}/{path}')
        self.image.setText(f'等待 {channel} 实时画面')

    def view_tab_changed(self, index):
        channel = 'LIDAR' if index == 1 else (
            self.video_channel.currentData() if self.video_channel.currentData() != 'LIDAR' else 'CH1')
        blocker = QSignalBlocker(self.video_channel)
        self.video_channel.setCurrentIndex(self.video_channel.findData(channel))
        del blocker
        self.switch_video_channel()

    def video_frame(self, image, fps):
        self.image.show_image(image)
        channel = self.video_channel.currentData() or 'CH1'
        modality = '可见光' if channel == 'CH1' else '红外'
        target_fps = self.config.rtsp_visible_fps if channel == 'CH1' else self.config.rtsp_infrared_fps
        self.image_caption.setText(
            f'{channel} {modality} · RTSP 实时 · {fps:.1f} FPS（目标 {target_fps}）')

    def video_state_changed(self, connected, message):
        if not connected and self.video_channel.currentData() != 'LIDAR':
            channel = self.video_channel.currentData() or 'CH1'
            self.image_caption.setText(f'{channel} · {message}')

    def completed(self, command, state):
        if command == 'sim.load_scene':
            self.switch_target = state.get('pending_scene')
            if not self.switch_target:
                self.log('UE 未返回切换目标，请检查引擎版本。')
                return
            self.switch_deadline = time.monotonic() + 90
            self.reconnect_timer.start()
            self.switch_button.setEnabled(False)
            self.image.source = QPixmap()
            self.image.clear()
            self.image.setText('正在切换场景，连接恢复后请重新获取画面')
            self.last_image_path = None
            self.image_caption.setText('场景切换中；旧场景画面已清除')
            self.log('UE 已接受场景切换，正在等待新地图与连接恢复…')
            return
        if command == 'sensor.lidar.get_points':
            point_count = state.get('lidar_point_count', 0)
            self.lidar.set_points(state.get('lidar_points_m', []), point_count)
            if self.video_channel.currentData() == 'LIDAR':
                self.image_caption.setText(
                    f"LIDAR 激光点云 · 实时 · {point_count} 个回波点 · 最近 {state.get('lidar_nearest_m', 0):.1f} m")
        elif command == 'sensor.lidar.capture':
            self.capture_button.setEnabled(self.client.ready)
            point_count = state.get('lidar_point_count', state.get('lidar_hits', 0))
            self.log(f"已保存激光点云：{point_count} 个点 · {state.get('point_cloud_path', 'UE Saved/WISEYE')}")
        elif command == 'camera.capture':
            self.capture_button.setEnabled(self.client.ready)
            path = Path(state['frame_path']).resolve()
            allowed = (ROOT/'ue5/WISEYE/Saved/WISEYE').resolve()
            if not path.is_relative_to(allowed) or path.suffix.lower() != '.png':
                self.log('截图不在当前工程输出目录，未打开。')
                return
            image = QPixmap(str(path))
            if image.isNull() or (image.width(), image.height()) != (state['width'], state['height']):
                self.log('截图读取失败或尺寸不一致。')
                return
            self.last_image_path = path
            self.image.show_image(image)
            mode = '可见光' if state['sensor_mode']=='visible' else ('红外白热' if state['palette']=='white_hot' else '红外黑热')
            self.image_caption.setText(f'{mode} · {image.width()} × {image.height()} · {datetime.now():%H:%M:%S} 获取的截图')
            self.log(f'已获取 {mode} 画面：{path.name}')
        elif command not in ('sim.get_state', 'sim.ping'):
            names = {'sim.pause':'仿真暂停','sim.resume':'仿真继续','sim.reset':'航线复位',
                      'flight.set_mode':'飞行模式','gimbal.set_tracking':'云台状态',
                       'drone.set_model':'无人机型号', 'sensor.set_active':'工作传感器',
                      'rotors.set_enabled':'旋翼状态','camera.set_mode':'相机模式',
                     'camera.set_palette':'红外调色板','camera.set_fov':'相机视场'}
            self.log(f"{names.get(command,command)}：UE 已确认")

    def air_completed(self, command, state):
        if command in ('sim.get_state', 'sim.ping', 'flight.set_input'):
            return
        names = {'sim.pause': 'AirSim 动力学暂停', 'sim.resume': 'AirSim 动力学继续',
                 'sim.reset': 'AirSim 正在返回航线原点', 'flight.set_mode': 'AirSim 飞行模式',
                 'flight.takeoff': '无人机起飞', 'flight.hover': '无人机悬停', 'flight.land': '无人机降落'}
        self.log(f"{names.get(command, command)}：已确认")

    def air_failed(self, command, message):
        if command == 'sim.ping' and not self.client.ready:
            return
        self.log(f'AirSim 操作失败：{message}')

    def failed(self, command, message):
        self.log(f'操作失败：{message}')
        if command in ('camera.capture', 'sensor.lidar.capture'):
            self.capture_button.setEnabled(self.client.ready)

    def closeEvent(self, event):
        self.reconnect_timer.stop()
        self.lidar_poll.stop()
        self.manual_timer.stop()
        self.manual_keys.clear()
        self.video_client.stop()
        self.air_client.disconnect_from(quiet=True)
        self.client.disconnect_from()
        super().closeEvent(event)

    def refresh_scenes(self):
        previous = (self.scenes.currentData() or {}).get('id')
        self.scenes.clear()
        scenes, _ = SceneStore(ROOT).list()
        for scene in scenes:
            if scene['installed']:
                self.scenes.addItem(scene['name'], scene)
                if scene['id'] == previous:
                    self.scenes.setCurrentIndex(self.scenes.count()-1)

    def manage_scenes(self):
        from apps.desktop_app.scene_dialog import SceneDialog
        SceneDialog(self).exec()
        self.refresh_scenes()

    def switch_scene(self):
        if self.switch_target:
            return
        scene = self.scenes.currentData()
        if scene:
            self.command('sim.load_scene', {'scene_id': scene['id']})

    def reconnect_scene(self):
        if not self.switch_target:
            self.reconnect_timer.stop()
            return
        if time.monotonic() > self.switch_deadline:
            self.reconnect_timer.stop()
            self.switch_target = None
            self.switch_button.setEnabled(self.client.ready)
            self.log('场景切换未在 90 秒内确认；请检查 UE 地图加载结果，再手动连接。')
        elif not self.client.ready and self.client.connect_deadline is None:
            self.client.connect_to(self.host.text().strip(), self.port.value())
