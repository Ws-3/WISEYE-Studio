import logging
import math
import time
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QEvent, QSignalBlocker, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QFrame, QHBoxLayout,
    QVBoxLayout, QGridLayout, QSplitter, QTabWidget, QScrollArea, QApplication, QAbstractSpinBox,QAbstractItemView)
from core.config import ROOT
from core.scenes import SceneStore
from apps.desktop_app.client import UEClient
from apps.desktop_app.airsim_client import AirSimClient
from apps.desktop_app.rtsp_client import RTSPVideoClient
from apps.desktop_app.lidar_view import LidarView

from apps.desktop_app.ui.theme import STYLE

from apps.desktop_app.image_view import ImageView

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle('WISEYE Studio · 智瞳控制台')
        self.resize(1600, 1000)
        from PySide6.QtGui import QAction,QKeySequence
        self.fullscreen_action=QAction('全屏显示',self);self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setShortcut(QKeySequence('F11'));self.addAction(self.fullscreen_action)
        self.fullscreen_action.toggled.connect(lambda full:self.showFullScreen() if full else self.showMaximized())
        self.setMinimumSize(960, 640)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(STYLE)
        self.client = UEClient(config, self)
        self.air_client = AirSimClient(config, self)
        self.video_client = RTSPVideoClient(self)
        self.infrared_client = RTSPVideoClient(self)
        self.observer_client=RTSPVideoClient(self)
        self.gimbal_stick_input=(0.,0.)
        self.gimbal_keys=set()
        self.gimbal_timer=QTimer(self);self.gimbal_timer.setInterval(100);self.gimbal_timer.timeout.connect(self.send_gimbal_input)
        self.config = config
        self.selected_drone="uav-01"
        self.selected_gimbal="ptz-01"
        self.device_switching=False
        from core.simulation_health import SimulationHealth
        self.health=SimulationHealth();self.simulation_healthy=False
        self.state = {}
        self.air_state = {}
        self.last_air_connect_attempt = 0.0
        self.stream_sample = None
        self.stream_fps = {}
        self.control_widgets = []
        self.flight_widgets = []
        self.last_image_path = None
        self.switch_target = None
        self.switch_run_id = None
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
        QApplication.instance().installEventFilter(self)
        from apps.desktop_app.language import manager
        manager()
        self._build(config)
        from apps.desktop_app.loading_screen import LoadingScreen
        self.loading_screen=LoadingScreen(self)
        manager().register(self)
        self.health_timer=QTimer(self);self.health_timer.setInterval(500)
        self.health_timer.timeout.connect(self.check_health);self.health_timer.start()
        self.client.connection_changed.connect(self.connection_changed)
        self.client.state_received.connect(self.apply_state)
        self.client.completed.connect(self.completed)
        self.client.failed.connect(self.failed)
        self.client.latency_changed.connect(lambda value: self.latency.setText(f'响应 {value:.0f} ms'))
        self.air_client.connection_changed.connect(self.air_connection_changed)
        self.air_client.state_received.connect(self.apply_air_state)
        self.air_client.completed.connect(self.air_completed)
        self.air_client.failed.connect(self.air_failed)
        self.connection_changed(False, '未连接')
        from core.runtime_paths import IS_RELEASE
        import os
        self.log('工作台已启动，UE 正在自动启动…' if os.environ.get('WISEYE_SESSION_STATUS') else
                 '工作台已启动，尚未启动 UE。点击右上角“启动仿真”，或在连接设置中连接已有仿真。')
        from apps.desktop_app.startup_status import watch_startup
        watch_startup(self)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'tree_panel'):
            narrow=self.width()<1440
            if getattr(self,'_narrow',None)!=narrow:
                aerial=getattr(getattr(self,'mission_workspace',None),'mode',None)=='aerial'
                self.tree_panel.setVisible(not narrow and not aerial)
                self._narrow=narrow

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
        from apps.desktop_app.workbench_v3 import build_workbench
        build_workbench(self, config, ImageView)

    def check_health(self):
        healthy,message=self.health.status(time.monotonic(),self.client.ready)
        changed=healthy!=self.simulation_healthy
        self.simulation_healthy=healthy
        self.health_label.setText(message)
        self.health_label.setStyleSheet('color:#89e1af' if healthy else 'color:#ffbf69')
        if self.client.ready:
            self.badge.setText('已连接 · 断开' if healthy else '推进异常 · 断开')
            self.badge.setStyleSheet('color:#76d6a0;' if healthy else 'color:#e6b76c;')
            self.badge.setToolTip(message)
        if changed and not healthy and self.client.ready:
            self.clear_gimbal_input()
            self.manual_keys.clear();self.manual_input=(0.,0.,0.,0.);self.send_manual_input()
            self.log(message+'；已清除持续操控输入，请检查 UE。')
        if not healthy and self.client.ready:
            self.summary_values['simulation'][0].setText('运行异常 · 请检查 UE')

    def log(self, message):
        self.logs.appendPlainText(f'{datetime.now():%H:%M:%S}  {message}')
        self.event_preview.setText(str(message)[:80])
        self.event_preview.setToolTip(str(message))
        logging.info(message)

    def connect_ue(self):
        host = self.host.text().strip()
        if not host:
            self.log('请填写 UE 地址。')
            return
        self.client.connect_to(host, self.port.value())
        self.air_client.connect_to(host)

    def disconnect_ue(self):
        self.clear_gimbal_input();self.manual_keys.clear();self.stop_manual_input()
        self.switch_target=None;self.reconnect_timer.stop()
        self.air_client.disconnect_from();self.client.disconnect_from()

    def toggle_connection(self):
        if self.client.ready or self.client.connect_deadline is not None:self.disconnect_ue()
        else:self.connect_ue()

    def toggle_simulation(self):
        manager=getattr(self,'runtime_manager',None)
        if manager and manager.running:
            self.clear_gimbal_input();self.manual_keys.clear();self.stop_manual_input()
            manager.closing=True;manager.stop();self.sync_session_buttons()
            self.log('正在安全关闭本次仿真，请等待降落和进程退出。')
        else:self.launch_ue()

    def sync_session_buttons(self):
        manager=getattr(self,'runtime_manager',None)
        running=bool(manager and manager.running)
        closing=bool(running and manager.closing)
        self.quick_connect.setText('正在关闭…' if closing else '关闭仿真' if running else '启动仿真')
        self.quick_connect.setEnabled(not closing and (running or not self.client.ready))
        self.quick_connect.setToolTip('安全关闭本次启动的仿真，等待无人机降落。' if running else
                                     '已有外部仿真时可连接；外部进程请从其窗口关闭。' if self.client.ready else '启动所选场景，不改变连接配置。')
        connecting=self.client.connect_deadline is not None
        self.badge.setText('已连接 · 断开' if self.client.ready else '连接中 · 取消' if connecting else '未连接 · 连接')
        self.badge.setEnabled(not closing)

    def runtime_stopped(self):
        self.disconnect_ue();self.sync_session_buttons()

    def runtime_ready(self):
        manager=getattr(self,'runtime_manager',None)
        if manager and manager.running and not manager.closing:self.connect_ue()

    def launch_ue(self):
        if self.client.ready:
            self.log('UE 已连接，请使用场景切换。');return
        if not hasattr(self, 'runtime_manager'):
            from apps.desktop_app.runtime_manager import RuntimeManager
            self.runtime_manager = RuntimeManager(self)
            self.runtime_manager.message.connect(self.log)
            self.runtime_manager.ready.connect(self.runtime_ready)
            self.runtime_manager.stopped.connect(self.runtime_stopped)
            self.runtime_manager.phase.connect(self.loading_screen.phase)
            self.runtime_manager.failed.connect(self.loading_screen.fail)
            self.runtime_manager.stopped.connect(self.loading_screen.stopped)
        if not self.runtime_manager.running:self.loading_screen.begin(self.scenes.currentData() or {'id':'city'})
        self.runtime_manager.launch(self.scenes.currentData() or {'id':'city'})
        self.sync_session_buttons()

    def connection_changed(self, connected, text):
        self.badge.setToolTip(text)
        self.badge.setStyleSheet('color:#76d6a0;' if connected else 'color:#b4bcc8;')
        self.sync_session_buttons()
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
            self.clear_gimbal_input()
            self.gimbal_stick.setEnabled(False)
            self.sensor_settings.disconnected()
            self.gallery.disconnected()
            self.observer_client.stop()
            self.lidar_poll.stop()
            self.video_client.stop()
            self.infrared_client.stop()
            self.active_scene.setText('当前场景：切换中' if self.switch_target else '当前场景：未连接')
            self.state = {}
            self.arrangement.tools.disconnected()
            self.sensor_applied.setText('实际参数：连接已断开，状态不可用')
            self.source_urls.setPlainText('仿真未连接，运行状态不可用。')
            self.distance_label.setText('距所选云台：未连接')
            self.lidar.set_points([], 0, 0)
            self.dual_infrared.source=QPixmap();self.dual_infrared.clear()
            self.dual_visible.source = QPixmap()
            self.dual_visible.clear()
            self.dual_visible.setText('仿真未连接')
            self.image.source = QPixmap()
            self.image.clear()
            self.image.setText('连接已断开 · 图像不可用')
            self.performance.setText('连接已断开；性能统计不可用。')
            self.stream_sample, self.stream_fps = None, {}
            for value, detail in self.summary_values.values():
                value.setText('—')
                detail.setText('状态不可用')
            self.angle_label.setText('偏航 —  /  俯仰 —')
            self.position_label.setText('无人机位置：—')
            self.latency.setText('响应 —')
            self.image_caption.setText('连接已断开 · 画面不可用；已保存文件仍保留在磁盘')
        else:
            self.gallery.sync_clients()
            self.sensor_settings.render()
        self.update_flight_controls()
        self.log(text)

    def air_connection_changed(self, connected, text):
        self.air_connection_detail.setText(text)
        if not connected:
            self.air_state = {}
        self.update_flight_controls()
        self.log(text)

    def command(self, command, payload=None):
        payload=dict(payload or {})
        movement=command in ('flight.set_input','gimbal.set_input','observer.set_input')
        if not self.simulation_healthy and ((movement and any(payload.get(k,0) for k in ('forward','right','up','yaw','pitch','yaw_deg','pitch_deg'))) or command in ('flight.takeoff','route.start','sim.resume')):
            self.log('仿真进度异常，暂不发送运动指令。');return
        drone_command=command.startswith(('flight.','route.','drone.','rotors.')) or command in ('sim.pause','sim.resume','sim.reset')
        payload.setdefault('device_id',self.selected_drone if drone_command else self.selected_gimbal)
        if self.device_switching and command.startswith(('gimbal.','sensor.','camera.')):
            self.log('云台切换中，请等待实际状态确认。');return
        if not self.client.ready:
            self.log('请先连接 UE。')
            return
        is_airsim = self.state.get('flight_backend') == 'projectairsim'
        flight_command = command in ('sim.pause', 'sim.resume', 'sim.reset', 'flight.takeoff',
                                     'flight.hover', 'flight.land', 'flight.set_mode', 'flight.set_input') or command.startswith('route.')
        if is_airsim and flight_command:
            if not self.air_client.ready:
                self.log('AirSim 飞控尚未连接，请从 Start-ProjectAirSim 启动仿真。')
                return
            if command in ('flight.takeoff','flight.land','flight.hover'):
                if any(c==command for c,_ in self.air_client.pending.values()):
                    self.log('同一动作正在等待确认。');return
                button={'flight.takeoff':self.takeoff_button,'flight.land':self.land_button,'flight.hover':self.hover_button}[command]
                button.setEnabled(False)
            self.air_client.request(command, payload)
        else:
            self.client.request(command, payload)
        if command in ('camera.capture', 'sensor.lidar.capture','sensor.event.capture'):
            self.capture_button.setEnabled(False)

    def capture_sensor(self,sensor):
        self.capture_source(self.selected_gimbal,sensor)

    def capture_source(self,device,sensor):
        if any(command in ('camera.capture','sensor.lidar.capture','sensor.event.capture') for command,_ in self.client.pending.values()):
            self.log('正在保存数据，请等待当前保存完成。');return
        actual=self.gallery.states.get(device,self.state if device==self.selected_gimbal else {})
        if not actual.get('sensors',{}).get(sensor,{}).get('enabled',False):
            self.log('该传感器已停用，请先启用并应用设置。');return
        if not self.client.ready:
            self.log('请先连接 UE。');return
        self.command('sensor.event.capture' if sensor=='event' else 'sensor.lidar.capture' if sensor=='lidar' else 'camera.capture',dict(device_id=device,**({} if sensor in ('lidar','event') else {'sensor':sensor})))

    def capture_active_sensor(self):
        self.capture_sensor(('visible','infrared','lidar','event')[self.sensor_settings.currentIndex()])

    def apply_state(self, state):
        self.fleet_selection.inventory(state)
        if state.get('gimbal_id','ptz-01')!=self.selected_gimbal:return
        self.device_switching=False
        self.health.observe(state,time.monotonic());self.check_health()
        blocker=QSignalBlocker(self.performance_profile)
        self.performance_profile.setCurrentIndex(self.performance_profile.findData(state.get('performance_profile','balanced')))
        del blocker
        self.state = state
        blocker=QSignalBlocker(self.tracking_target);self.tracking_target.setCurrentIndex(self.tracking_target.findData(state.get('tracking_target','uav-01')));del blocker
        self.arrangement.tools.apply_state(state)
        for combo, key in ((self.input_mode, 'input_mode'), (self.observer_mode, 'observer_mode')):
            if key in state:
                blocker = QSignalBlocker(combo)
                combo.setCurrentIndex(combo.findData(state[key]))
                del blocker
        self.gimbal_stick.setEnabled(self.client.ready and state.get('input_mode')=='gimbal')
        self.gimbal_pitch.setRange(state.get('pitch_min_deg', -15), state.get('pitch_max_deg', 75))
        if state.get('input_mode')!='gimbal' and (self.gimbal_keys or any(self.gimbal_stick_input)):self.clear_gimbal_input()
        for channel,sensor in [('CH1','visible'),('CH2','infrared')]:
            if state.get('sensors',{}).get(sensor,{}).get('enabled') is False:
                legacy=self.dual_visible if channel=='CH1' else self.dual_infrared
                legacy.source=QPixmap();legacy.clear();legacy.setText('该传感器已停用')
                if self.video_channel.currentData()==channel:self.image.source=QPixmap();self.image.clear();self.image.setText('该传感器已停用')
        if state.get('lidar_enabled') is False:
            self.lidar.set_points([],0,0)
        streams = state.get('streams', {})
        sample = (state.get('run_id'), time.monotonic(), {key:value['completed_frames'] for key,value in streams.items()})
        if self.stream_sample and sample[0] == self.stream_sample[0] and sample[1]-self.stream_sample[1] >= 2:
            dt = sample[1]-self.stream_sample[1]
            self.stream_fps = {key:max(0,count-self.stream_sample[2].get(key,count))/dt for key,count in sample[2].items()}
            self.stream_sample = sample
        elif not self.stream_sample or sample[0] != self.stream_sample[0]:
            self.stream_sample, self.stream_fps = sample, {}

        hints = {
            'observer':'观察模式：点击画面上的自由观察，按住右键 + WASD 移动，Q/E 升降；也支持独立 UE 窗口观察。',
            'drone':'驾驶模式：系统与 UE 均为 W/S 前后、A/D 左右、R/F 上升/下降、Q/E 转向。',
            'gimbal':'云台模式：桌面与 UE 方向键转动；松键或失焦停止，可输入目标角度。'}
        self.input_hint.setText(hints.get(state.get('input_mode'), '等待输入模式确认'))
        self.sensor_applied.setText(f'{self.selected_gimbal} · 各传感器独立应用与保存')
        self.drone_control_label.setText('控制对象：'+self.selected_drone)
        host = self.host.text().strip() or self.config.host
        source_text = (f"可见光 · 1920 × 1080\n{self.config.stream_url(self.selected_gimbal, 'visible')}\n\n"
                       f"红外 · 640 × 512\n{self.config.stream_url(self.selected_gimbal, 'infrared')}\n\n"
                       f"UE / 点云 JSON Lines · {host}:{self.port.value()}\n飞控 JSON Lines · {host}:{self.config.airsim_port}\n"
                       f"对象：{self.selected_drone} / {self.selected_gimbal}\n会话：{state.get('run_id', '未提供')}\n"
                       f"UE 观察 · 960 × 540\n{self.config.stream_url('scene', 'observer')}\n"
                       "红外：合成热成像；点云：米制局部坐标，详见 docs/PROTOCOL.md")
        if self.source_urls.toPlainText() != source_text:
            self.source_urls.setPlainText(source_text)
        if not self.client.ready:
            return
        if self.air_state.get('run_id') and state.get('run_id') and self.air_state['run_id'] != state['run_id']:
            self.air_state = {}
            self.air_client.disconnect_from()
        scene_id = state.get('scene_id', '旧版 UE 未提供场景信息')
        if (state.get('flight_backend') == 'projectairsim' and not self.air_client.ready
                and self.air_client.connect_deadline is None
                and time.monotonic() - self.last_air_connect_attempt >= 3.0):
            self.last_air_connect_attempt = time.monotonic()
            self.air_client.connect_to(self.host.text().strip())
        self.active_scene.setText('当前场景：' + scene_id)
        if self.switch_target and scene_id == self.switch_target and (not self.switch_run_id or state.get('run_id') != self.switch_run_id):
            self.log('场景切换完成，已恢复 UE 连接：' + scene_id)
            self.switch_target = None
            self.reconnect_timer.stop()
            self.switch_button.setEnabled(True)
        value, detail = self.summary_values['simulation']
        paused = self.air_state.get('paused', state['paused']) if state.get('flight_backend') == 'projectairsim' else state['paused']
        mode = self.air_state.get('flight_mode', state['flight_mode']) if state.get('flight_backend') == 'projectairsim' else state['flight_mode']
        value.setText('待命 · 请起飞' if self.air_state.get('flight_status') == 'ready' else '已暂停' if paused else '运行中')
        backend = 'AirSim' if state.get('flight_backend') == 'projectairsim' else '运动学'
        detail.setText(f"{backend} · 航线时间 {state['simulation_time_s']:.1f} s · {'自动' if mode=='auto' else '手动'}")
        value, detail = self.summary_values['gimbal']
        value.setText('目标跟踪' if state['tracking'] else '方向保持')
        detail.setText(f"指向误差 {state['pointing_error_deg']:.3f}° · 真值指向")
        value, detail = self.summary_values['sensor']
        active_sensor = state.get('active_sensor', state['sensor_mode'])
        sensor_names = {'visible': '可见光', 'infrared': '红外', 'lidar': '激光雷达','event':'事件相机'}
        self.capture_button.setText('保存当前传感器页数据')
        value.setText(f"{sum(bool(v.get('enabled')) for v in state.get('sensors',{}).values())} / {len(state.get('sensors',{}))} 启用")
        if active_sensor == 'lidar':
            detail.setText(
                f"回波 {state.get('lidar_hits',0)}/{state.get('lidar_rays',0)} · 最近 {state.get('lidar_nearest_m',0):.1f} m")
        else:
            detail.setText(f"{state['width']} × {state['height']} · 激光 {state.get('lidar_hits',0)}/{state.get('lidar_rays',0)}")
        display_state = dict(state)
        display_state['flight_mode'] = mode
        display_state['active_sensor'] = active_sensor
        for combo, key in [(self.flight, 'flight_mode')]:
            blocker = QSignalBlocker(combo)
            combo.setCurrentIndex(combo.findData(display_state[key]))
            del blocker
        model=next((d['model_id'] for d in state.get('devices',[]) if d['id']==self.selected_drone),state.get('drone_model','mavic3'))
        blocker = QSignalBlocker(self.drone_model)
        self.drone_model.setCurrentIndex(max(0, self.drone_model.findData(model)))
        del blocker
        self.pause_button.setEnabled(not paused)
        self.resume_button.setEnabled(paused)
        self.tracking_button.setText('保持云台方向' if state['tracking'] else '恢复目标跟踪')
        physics=state.get('flight_backend')=='projectairsim'
        rpm=next((d.get('motor_rpm') for d in self.air_state.get('fleet',[]) if d.get('drone_id')==self.selected_drone),None) or self.air_state.get('motor_rpm',[])
        self.motor_label.setText(('电机 RPM：'+' / '.join(f'{v:.0f}' for v in rpm)) if physics and rpm else '电机转速：等待遥测' if physics else '运动学旋翼动画')
        if self.air_state.get('airframe')=='fixedwing':self.motor_label.setText(f"JSBSim 巡航 · {self.air_state.get('velocity_mps',0):.1f} m/s · 未模拟电机转速")
        self.rotors_button.setText('停止旋翼动画' if state['rotors_running'] else '启动旋翼动画')
        self.rotors_button.setVisible(not physics)
        self.rotors_button.setEnabled(not physics)
        self.angle_label.setText(f"偏航 {state['yaw_deg']:.1f}°  /  俯仰 {state['pitch_deg']:.1f}°")
        ned=self.air_state.get('position_ned_m')
        position=[ned[0]*100,ned[1]*100,-ned[2]*100] if ned else next((d['position_cm'] for d in state.get('devices',[]) if d['id']==self.selected_drone),state['drone_position_cm'])
        self.position_label.setText(f'{self.selected_drone} 位置（m）\nX {position[0]/100:.2f} · Y {position[1]/100:.2f} · Z {position[2]/100:.2f}')
        gimbal=next((d for d in state.get('devices',[]) if d['id']==self.selected_gimbal and d['kind']=='gimbal'),None)
        base=gimbal.get('position_cm') if gimbal else state.get('gimbal_position_cm') if state.get('gimbal_id')==self.selected_gimbal else None
        if base and len(base)==3:
            dx,dy,dz=[(float(a)-float(b))/100 for a,b in zip(position,base)]
            self.distance_label.setText(f'{self.selected_drone} → {self.selected_gimbal}\n三维距离 {math.sqrt(dx*dx+dy*dy+dz*dz):.2f} m · 水平 {math.hypot(dx,dy):.2f} m\n高差 {dz:+.2f} m')
            self.distance_label.setToolTip('UE世界坐标几何真值；以所选云台底座为参考，不是激光测距回波。')
        else:self.distance_label.setText('距所选云台：等待设备坐标')
        from apps.desktop_app.workbench_v3 import update_sources, refresh_inspector
        update_sources(self)
        refresh_inspector(self)
        self.update_flight_controls()

    def apply_air_state(self, state):
        if state.get('drone_id',self.selected_drone)!=self.selected_drone:return
        if state.get('run_id') and self.state.get('run_id') and state['run_id'] != self.state['run_id']:
            self.air_state = {}
            self.air_client.disconnect_from()
            self.update_flight_controls()
            return
        self.air_state = state
        if self.state:
            self.apply_state(self.state)
        if state.get('last_error'):
            self.air_connection_detail.setText('AirSim 飞控：' + state['last_error'])

    def update_flight_controls(self):
        is_airsim = self.state.get('flight_backend') == 'projectairsim'
        available = self.client.ready and (not is_airsim or (self.air_client.ready and self.air_state.get('drone_id')==self.selected_drone)) and not self.state.get('placement', {}).get('active', False)
        mode = self.air_state.get('flight_mode', self.state.get('flight_mode'))
        paused = self.air_state.get('paused', self.state.get('paused', False))
        if (not available or mode != 'manual' or paused or self.input_mode.currentData() != 'drone') and (self.manual_keys or self.manual_timer.isActive()):
            self.manual_keys.clear()
            self.stop_manual_input()
        for widget in self.flight_widgets:
            widget.setEnabled(available)
        self.pause_button.setEnabled(available and not paused)
        self.resume_button.setEnabled(available and paused and self.air_state.get('flight_status') != 'ready')
        for widget in self.flight_widgets:
            if widget not in (self.pause_button, self.resume_button, self.reset_button, self.flight,
                              self.takeoff_button, self.hover_button, self.land_button):
                widget.setEnabled(available and mode == 'manual' and not paused and self.input_mode.currentData() == 'drone')
        status=self.air_state.get('flight_status','unknown')
        active=self.air_state.get('command_active',False)
        if is_airsim:
            self.takeoff_button.setEnabled(available and status=='ready' and not active and self.simulation_healthy)
            self.hover_button.setEnabled(available and status!='ready')
            self.land_button.setEnabled(available and status not in ('ready','landing'))
            for widget in self.flight_widgets:
                if widget not in (self.pause_button,self.resume_button,self.reset_button,self.flight,self.takeoff_button,self.hover_button,self.land_button):
                    widget.setEnabled(widget.isEnabled() and status!='ready')
        names={'ready':'地面待命','active':'已离地','taking_off':'起飞中','hovering':'悬停','manual':'手动飞行','landing':'降落中','flying':'飞行中','unknown':'状态待确认'}
        self.flight_status_label.setText(names.get(status,status)+(' · 动作执行中' if active else ''))
        collision_stop=self.air_state.get('airframe')=='fixedwing' and 'obstacle' in self.air_state.get('last_error','').lower()
        if collision_stop:
            self.flight_status_label.setText('固定翼碰撞保护停止 · 返回起点后重新巡航')
            self.resume_button.setEnabled(False)
        self.reset_button.setText('碰撞后返回起点' if collision_stop else '返回起点')
        self.manual_takeover.setEnabled(available and (not is_airsim or status!='ready') and (not active or mode=='auto'))
        self.takeoff_button.setToolTip('仅地面待命、飞控就绪且仿真推进正常时可起飞。')
        fixed=self.air_state.get('airframe')=='fixedwing'
        mapping={'前进':'加速 W','后退':'减速 S','向左':'左转 A','向右':'右转 D','左转':'左转 Q','右转':'右转 E','悬停':'平飞'}
        for button,title in getattr(self,'manual_axis_buttons',[]):button.setText(mapping.get(title,title) if fixed else title)
        if hasattr(self,'manual_move_hint'):self.manual_move_hint.setText('固定翼：W/S渐变调速，A/D或Q/E转弯，R/F升降；松手自动回平并保持速度。' if fixed else '按住按钮移动 · 松开停止')
        self.takeoff_button.setText('开始巡航' if fixed else '起飞')
        self.hover_button.setText('盘旋等待' if fixed else '悬停')
        self.land_button.setText('停止巡航' if fixed else '降落')
        if fixed:
            self.takeoff_button.setToolTip('空中初始化：从初始位置上方 30 m 开始巡航；这不是物理起飞。')
            self.land_button.setToolTip('停止运动预览并保持当前位置；这不是物理降落。')
            self.flight_status_label.setText('待开始巡航' if status=='ready' else 'JSBSim 六自由度 · 参数未标定')


    def poll_lidar(self):
        if (self.client.ready and self.state.get('lidar_enabled', False)
                and not any(command == 'sensor.lidar.get_points'
                            for command, _ in self.client.pending.values())):
            self.client.request('sensor.lidar.get_points')

    def start_manual_input(self, vector):
        if self.input_mode.currentData() != 'drone':
            return
        self.manual_input = tuple(float(value) for value in vector)
        self.send_manual_input()
        self.manual_timer.start()

    def set_flight_mode(self, _index=None):
        self.manual_keys.clear()
        self.stop_manual_input()
        if self.flight.currentData()=='auto' and self.state.get('flight_backend')=='projectairsim':
            from apps.desktop_app.route_editor import open_route_editor
            open_route_editor(self)
            blocker=QSignalBlocker(self.flight)
            self.flight.setCurrentIndex(self.flight.findData(self.air_state.get('flight_mode','manual')))
            del blocker
            return
        if self.flight.currentData() == 'manual':
            self.command('input.set_mode', {'mode': 'drone'})
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

    def gimbal_key(self,key,pressed):
        if pressed:
            if not self.client.ready or self.state.get('input_mode')!='gimbal':return
            self.gimbal_keys.add(key)
        else:self.gimbal_keys.discard(key)
        self.send_gimbal_input()
        if self.gimbal_keys or any(self.gimbal_stick_input):self.gimbal_timer.start()
        else:self.gimbal_timer.stop()

    def set_gimbal_stick(self,yaw,pitch):
        if not self.client.ready or self.state.get('input_mode')!='gimbal':
            self.gimbal_stick_input=(0.,0.);return
        self.gimbal_stick_input=(yaw,pitch)
        self.send_gimbal_input()
        if any(self.gimbal_stick_input) or self.gimbal_keys:self.gimbal_timer.start()
        else:self.gimbal_timer.stop()

    def send_gimbal_input(self):
        if not self.simulation_healthy:
            self.gimbal_keys.clear();self.gimbal_stick_input=(0.,0.)
        if self.client.ready:
            self.client.request('gimbal.set_input',{'yaw':max(-1.,min(1.,self.gimbal_stick_input[0]+float((Qt.Key.Key_Right in self.gimbal_keys)-(Qt.Key.Key_Left in self.gimbal_keys)))),'pitch':max(-1.,min(1.,self.gimbal_stick_input[1]+float((Qt.Key.Key_Up in self.gimbal_keys)-(Qt.Key.Key_Down in self.gimbal_keys))))})

    def clear_gimbal_input(self):
        self.gimbal_keys.clear();self.gimbal_stick_input=(0.,0.);self.gimbal_timer.stop()
        blocker=QSignalBlocker(self.gimbal_stick);self.gimbal_stick.reset();del blocker
        self.send_gimbal_input()

    def eventFilter(self, watched, event):
        cover=getattr(self,'loading_screen',None)
        if (cover and event.type() in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease,QEvent.Type.ShortcutOverride) and cover.isVisible()
                and isinstance(watched,QWidget) and (watched is self or self.isAncestorOf(watched))
                and event.key() in (Qt.Key.Key_W,Qt.Key.Key_S,Qt.Key.Key_A,Qt.Key.Key_D,Qt.Key.Key_Q,Qt.Key.Key_E,Qt.Key.Key_R,Qt.Key.Key_F,Qt.Key.Key_Up,Qt.Key.Key_Down,Qt.Key.Key_Left,Qt.Key.Key_Right)):
            event.accept();return True
        mission=getattr(self,'mission_workspace',None)
        if mission and event.type() in (QEvent.Type.WindowDeactivate,QEvent.Type.FocusOut):mission.stop_keys()
        if (event.type()==QEvent.Type.KeyPress and isinstance(watched,QWidget)
                and (watched is self or self.isAncestorOf(watched)) and event.key()==Qt.Key.Key_Escape):
            self.clear_gimbal_input();self.manual_keys.clear();self.stop_manual_input()
            for view in self.gallery.views.values():
                if hasattr(view,'stop'):view.stop()
        if watched is self and event.type()==QEvent.Type.WindowDeactivate:self.clear_gimbal_input()
        if isinstance(watched,QWidget):
            ancestor=watched
            while ancestor is not None:
                if ancestor.property('observerInput') and not (mission and mission.mode=='aerial'):return super().eventFilter(watched,event)
                ancestor=ancestor.parentWidget()
        if (event.type() in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease,QEvent.Type.ShortcutOverride) and isinstance(watched,QWidget)
                and (watched is self or self.isAncestorOf(watched)) and event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Up,Qt.Key.Key_Down)):
            focus=QApplication.focusWidget()
            editing=isinstance(focus,(QLineEdit,QAbstractSpinBox,QComboBox,QAbstractItemView)) or (isinstance(focus,QPlainTextEdit) and not focus.isReadOnly())
            release=event.type()==QEvent.Type.KeyRelease and event.key() in self.gimbal_keys
            if mission and mission.mode=='aerial' and (event.key() in mission.aim_keys or (self.client.ready and not editing and not QApplication.activePopupWidget())):
                return mission.handle_key(event)
            if release or (self.client.ready and self.state.get('input_mode')=='gimbal' and not editing and not QApplication.activePopupWidget()):
                if not event.isAutoRepeat() and event.type()!=QEvent.Type.ShortcutOverride:self.gimbal_key(event.key(),event.type()==QEvent.Type.KeyPress)
                event.accept();return True

        keys = {Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D,
                Qt.Key.Key_R, Qt.Key.Key_F, Qt.Key.Key_Q, Qt.Key.Key_E}
        if watched is self and event.type() == QEvent.Type.WindowDeactivate:
            self.manual_keys.clear()
            self.stop_manual_input()
        if (event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.ShortcutOverride)
                and isinstance(watched, QWidget) and (watched is self or self.isAncestorOf(watched))
                and event.key() in keys):
            focus = QApplication.focusWidget()
            editing = isinstance(focus, (QLineEdit, QAbstractSpinBox,QComboBox,QAbstractItemView)) or (isinstance(focus, QPlainTextEdit) and not focus.isReadOnly())
            mode = self.air_state.get('flight_mode', self.state.get('flight_mode'))
            paused = self.air_state.get('paused', self.state.get('paused', False))
            available = self.client.ready and (self.state.get('flight_backend') != 'projectairsim' or self.air_client.ready)
            releasing = event.type() == QEvent.Type.KeyRelease and event.key() in self.manual_keys
            if releasing or (available and mode == 'manual' and self.input_mode.currentData() == 'drone' and not paused and not editing and not QApplication.activePopupWidget()):
                if not event.isAutoRepeat() and event.type() != QEvent.Type.ShortcutOverride:
                    if event.type() == QEvent.Type.KeyPress:
                        self.manual_keys.add(event.key())
                    else:
                        self.manual_keys.discard(event.key())
                    self._keyboard_manual_input()
                event.accept()
                return True
        return super().eventFilter(watched, event)

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
        mode = self.air_state.get('flight_mode', self.state.get('flight_mode'))
        if self.client.ready and mode == 'manual':
            forward, right, up, yaw = self.manual_input
            self.command('flight.set_input', {
                'forward': forward, 'right': right, 'up': up, 'yaw': yaw,
            })

    def switch_video_channel(self):
        self.gallery.sync_clients()

    def completed(self, command, state):
        if state.get('gimbal_id',self.selected_gimbal)!=self.selected_gimbal and command not in ('sim.load_scene','camera.capture','sensor.lidar.capture','sensor.event.capture'):return
        if command == 'sensor.lidar.set_parameters':
            self.lidar_dirty.clear()
            self.apply_state(state)
        if command == 'sim.load_scene':
            self.switch_run_id = state.get('run_id')
            self.switch_target = state.get('pending_scene')
            if not self.switch_target:
                self.log('UE 未返回切换目标，请检查引擎版本。')
                return
            self.loading_screen.begin({'id':self.switch_target,'name':self.switch_target},switch=True)
            self.switch_timeout_seconds = 900 if self.switch_target == 'city_large' else 90
            self.switch_deadline = time.monotonic() + self.switch_timeout_seconds
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
            self.lidar.set_points(state.get('lidar_points_m', []), point_count, state.get('lidar_rays', 0),
                                  state.get('lidar_horizontal_fov_deg',30),state.get('lidar_vertical_fov_deg',8))
            if self.video_channel.currentData() == 'LIDAR':
                self.image_caption.setText(
                    f"LIDAR 激光点云 · 实时 · {point_count} 个回波点 · 最近 {state.get('lidar_nearest_m', 0):.1f} m")
        elif command == 'sensor.event.capture':
            self.capture_button.setEnabled(self.client.ready)
            self.log(f"已保存最近事件窗口：{state.get('event_last_export_path','UE Saved/WISEYE')}")
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
            if image.isNull() or (image.width(), image.height()) != (state.get('frame_width',state['width']), state.get('frame_height',state['height'])):
                self.log('截图读取失败或尺寸不一致。')
                return
            self.last_image_path = path
            self.image.show_image(image)
            mode = '可见光' if state.get('frame_sensor',state['sensor_mode'])=='visible' else ('红外白热' if state['palette']=='white_hot' else '红外黑热')
            self.image_caption.setText(f'{mode} · {image.width()} × {image.height()} · {datetime.now():%H:%M:%S} 获取的截图')
            self.log(f'已获取 {mode} 画面：{path.name}')
        elif command not in ('sim.get_state', 'sim.ping','gimbal.set_input','observer.set_input'):
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
        self.arrangement.tools.failed(command, message)
        self.log(f'操作失败：{message}')
        if command in ('camera.capture', 'sensor.lidar.capture','sensor.event.capture'):
            self.capture_button.setEnabled(self.client.ready)

    def closeEvent(self, event):
        self.sensor_settings.stash()
        device_draft=hasattr(self,'device_page') and self.device_page.has_draft()
        if not getattr(self, '_exit_confirmed', False) and (device_draft or self.sensor_settings.pending or any(item.get('dirty') for item in self.sensor_settings.bank.values())):
            from PySide6.QtWidgets import QMessageBox
            answer=QMessageBox.question(self,'退出工作台','存在未保存的设备编辑、未应用的传感器草稿或尚未确认的提交。退出将丢弃本地草稿，已经发送的操作可能已生效。是否退出？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            if answer!=QMessageBox.StandardButton.Yes:
                event.ignore();return
        self._exit_confirmed = True
        self.runtime_panel.rating_timer.stop()
        manager = getattr(self, 'runtime_manager', None)
        if not getattr(self, '_training_job', None) and not (manager and manager.running):
            self._shutdown_complete = True
        if not getattr(self, '_shutdown_complete', False):
            event.ignore()
            if not getattr(self, '_shutdown_started', False):
                import threading
                from PySide6.QtCore import QTimer
                from apps.desktop_app.training_launcher import close_owned_training
                self._shutdown_started = True
                self.clear_gimbal_input(); self.stop_manual_input()
                self.log('正在停止训练采集并关闭本次启动的仿真，请稍候…')
                self.setEnabled(False)
                manager = getattr(self, 'runtime_manager', None)
                def finish():
                    try:
                        close_owned_training(self)
                    finally:
                        if manager and manager.running:
                            manager.stop()
                            while manager.running:time.sleep(.1)
                        self._shutdown_complete = True
                threading.Thread(target=finish, daemon=True).start()
                self._close_timer = QTimer(self)
                self._close_timer.timeout.connect(lambda: self.close() if getattr(self,'_shutdown_complete',False) else None)
                self._close_timer.start(100)
            return
        if getattr(self, '_close_timer', None):self._close_timer.stop()
        if getattr(self,'route_editor',None):self.route_editor.close()
        if hasattr(self,'machine_summary'):self.machine_summary.dialog.close()
        if getattr(self.runtime_panel,'dialog',None):self.runtime_panel.dialog.close()
        if getattr(self,'gimbal_device_dialog',None):self.gimbal_device_dialog.close()
        from apps.desktop_app.workbench_polish import AdvancedControl
        for section in self.findChildren(AdvancedControl):section.dialog.close()
        from PySide6.QtCore import QSettings
        QSettings('WISEYE','Studio').setValue('workbench/split',self.workbench_split.saveState())
        self.gallery.shutdown()
        self.observer_client.stop()
        self.clear_gimbal_input()
        self.arrangement.tools.cancel_pending()
        self.stop_manual_input()
        QApplication.instance().removeEventFilter(self)
        self.reconnect_timer.stop()
        self.lidar_poll.stop()
        self.manual_timer.stop()
        self.manual_keys.clear()
        self.video_client.stop()
        self.infrared_client.stop()
        self.air_client.disconnect_from(quiet=True)
        self.client.disconnect_from()
        super().closeEvent(event)

    def refresh_scenes(self):
        previous = (self.scenes.currentData() or {}).get('id') or 'city'
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
            self.log(f'场景切换未在 {self.switch_timeout_seconds} 秒内确认；请检查 UE 地图加载结果，再手动连接。')
            self.loading_screen.fail('场景切换超时，请检查运行日志和UE状态。')
        elif not self.client.ready and self.client.connect_deadline is None:
            self.client.connect_to(self.host.text().strip(), self.port.value())
