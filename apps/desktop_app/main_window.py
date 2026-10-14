import logging
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QSignalBlocker, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QFrame, QHBoxLayout,
    QVBoxLayout, QGridLayout, QSplitter)
from core.config import ROOT
from apps.desktop_app.client import UEClient

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
        super().__init__('尚未获取画面\n\n连接 UE 后，点击“获取当前画面”')
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(430, 260)
        self.setStyleSheet('background:#080f18; color:#71869e; border:1px solid #2b394d; border-radius:8px;')
        self.source = QPixmap()

    def show_image(self, image):
        self.source = image
        self._fit()

    def _fit(self):
        if not self.source.isNull():
            self.setPixmap(self.source.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle('WISEYE Studio · 智瞳控制台')
        self.resize(1320, 890)
        self.setMinimumSize(1080, 740)
        self.setStyleSheet(STYLE)
        self.client = UEClient(config, self)
        self.state = {}
        self.control_widgets = []
        self.last_image_path = None
        self._build(config)
        self.client.connection_changed.connect(self.connection_changed)
        self.client.state_received.connect(self.apply_state)
        self.client.completed.connect(self.completed)
        self.client.failed.connect(self.failed)
        self.client.latency_changed.connect(lambda value: self.latency.setText(f'响应 {value:.0f} ms'))
        self.connection_changed(False, '未连接')
        self.log('控制台已启动。请在 UE 中点击播放，再连接仿真。')

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
        self.connection_detail = self._label('等待连接')
        self.connection_detail.setWordWrap(True)
        side_layout.addWidget(self.connection_detail)
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
        image_header.addWidget(self._label('光电相机画面'))
        image_header.addStretch()
        self.capture_button = self._button('获取当前画面', lambda: self.command('camera.capture'), True)
        image_header.addWidget(self.capture_button)
        view_layout.addLayout(image_header)
        self.image = ImageView()
        view_layout.addWidget(self.image, 1)
        self.image_caption = self._label('当前显示截图；实时视频流待接入')
        self.image_caption.setWordWrap(True)
        view_layout.addWidget(self.image_caption)
        work.addWidget(view_card, 1)
        controls, layout = self._card()
        controls.setFixedWidth(290)
        layout.addWidget(self._label('仿真控制'))
        buttons = QHBoxLayout()
        self.pause_button = self._button('暂停', lambda: self.command('sim.pause'))
        self.resume_button = self._button('继续', lambda: self.command('sim.resume'))
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.resume_button)
        layout.addLayout(buttons)
        layout.addWidget(self._button('复位航线', lambda: self.command('sim.reset')))
        self.flight = QComboBox()
        self.flight.addItem('自动航线', 'auto')
        self.flight.addItem('手动飞行（UE 键盘）', 'manual')
        self.flight.activated.connect(lambda _: self.command('flight.set_mode', {'mode': self.flight.currentData()}))
        layout.addWidget(self.flight)
        self.control_widgets.append(self.flight)
        self.tracking_button = self._button('保持云台方向', lambda: self.command('gimbal.set_tracking', {'enabled': not self.state.get('tracking', True)}))
        self.rotors_button = self._button('停止旋翼', lambda: self.command('rotors.set_enabled', {'enabled': not self.state.get('rotors_running', True)}))
        layout.addWidget(self.tracking_button)
        layout.addWidget(self.rotors_button)
        layout.addWidget(self._label('相机设置'))
        self.sensor = QComboBox()
        self.sensor.addItem('可见光 · 1920 × 1080', 'visible')
        self.sensor.addItem('红外 · 640 × 512', 'infrared')
        self.sensor.activated.connect(lambda _: self.command('camera.set_mode', {'mode': self.sensor.currentData()}))
        layout.addWidget(self.sensor)
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
        work.addWidget(controls)
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

    def launch_ue(self):
        from PySide6.QtCore import QProcess
        started = QProcess.startDetached('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass',
                   '-File', str(ROOT/'scripts/Start-WISEYE.ps1'), '-SkipBuild'], str(ROOT))
        self.log('已请求打开 UE，请等待关卡加载后点击播放。' if started[0] else 'UE 启动失败，请检查引擎路径。')

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
        if not connected:
            self.state = {}
            for value, detail in self.summary_values.values():
                value.setText('—')
                detail.setText('状态不可用')
            self.angle_label.setText('偏航 —  /  俯仰 —')
            self.position_label.setText('无人机位置：—')
            self.latency.setText('响应 —')
            if self.last_image_path:
                self.image_caption.setText('连接已断开 · 保留上次截图，非当前画面')
        self.log(text)

    def command(self, command, payload=None):
        if not self.client.ready:
            self.log('请先连接 UE。')
            return
        self.client.request(command, payload)
        if command == 'camera.capture':
            self.capture_button.setEnabled(False)

    def apply_state(self, state):
        self.state = state
        if not self.client.ready:
            return
        value, detail = self.summary_values['simulation']
        value.setText('已暂停' if state['paused'] else '运行中')
        detail.setText(f"航线时间 {state['simulation_time_s']:.1f} s · {'自动' if state['flight_mode']=='auto' else '手动'}")
        value, detail = self.summary_values['gimbal']
        value.setText('目标跟踪' if state['tracking'] else '方向保持')
        detail.setText(f"指向误差 {state['pointing_error_deg']:.3f}° · 真值指向")
        value, detail = self.summary_values['sensor']
        value.setText('可见光' if state['sensor_mode']=='visible' else '红外')
        detail.setText(f"{state['width']} × {state['height']} · 视场 {state['fov_deg']:.1f}°")
        for combo, key in [(self.flight, 'flight_mode'), (self.sensor, 'sensor_mode'), (self.palette, 'palette')]:
            blocker = QSignalBlocker(combo)
            combo.setCurrentIndex(combo.findData(state[key]))
            del blocker
        if not self.fov.hasFocus():
            self.fov.setValue(state['fov_deg'])
        self.pause_button.setEnabled(not state['paused'])
        self.resume_button.setEnabled(state['paused'])
        self.palette.setEnabled(state['sensor_mode']=='infrared')
        self.tracking_button.setText('保持云台方向' if state['tracking'] else '恢复目标跟踪')
        self.rotors_button.setText('停止旋翼' if state['rotors_running'] else '启动旋翼')
        self.angle_label.setText(f"偏航 {state['yaw_deg']:.1f}°  /  俯仰 {state['pitch_deg']:.1f}°")
        position = state['drone_position_cm']
        self.position_label.setText(f'无人机位置（m）\nX {position[0]/100:.2f} · Y {position[1]/100:.2f} · Z {position[2]/100:.2f}')

    def completed(self, command, state):
        if command == 'camera.capture':
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
                     'rotors.set_enabled':'旋翼状态','camera.set_mode':'相机模式',
                     'camera.set_palette':'红外调色板','camera.set_fov':'相机视场'}
            self.log(f"{names.get(command,command)}：UE 已确认")

    def failed(self, command, message):
        self.log(f'操作失败：{message}')
        if command == 'camera.capture':
            self.capture_button.setEnabled(self.client.ready)

    def closeEvent(self, event):
        self.client.disconnect_from()
        super().closeEvent(event)
