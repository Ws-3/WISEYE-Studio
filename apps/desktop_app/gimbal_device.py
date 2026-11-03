"""Device telemetry, explicit simulation georeference and coordinate pointing."""
import math
from PySide6.QtCore import Qt,QSignalBlocker
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,
    QTabWidget,QWidget,QComboBox,QPushButton,QDoubleSpinBox,QScrollArea)
from core.config import ROOT
from core.georeference import GeoReference,GeoReferenceStore


def number(low,high,decimals=3,suffix=''):
    field=QDoubleSpinBox();field.setRange(low,high);field.setDecimals(decimals);field.setSuffix(suffix);return field


def position_text(position):return ' / '.join(f'{v/100:.3f}' for v in position)+' m'


class GimbalDeviceDialog(QDialog):
    def __init__(self,w):
        super().__init__(w);self.owner=w;self.device_id=w.selected_gimbal;self.last=None;self.pending=None;self.reference=None;self.scene_id=None
        self.store=GeoReferenceStore(ROOT);self.setWindowTitle('云台设备 · '+self.device_id);self.resize(680,760)
        root=QVBoxLayout(self);self.identity=QLabel(self.device_id);self.identity.setObjectName('value');root.addWidget(self.identity)
        self.tabs=QTabWidget();root.addWidget(self.tabs,1)
        telemetry=QWidget();form=QFormLayout(telemetry);form.setSpacing(12);self.values={}
        for key,title in [('frame','坐标说明'),('pose','云台实际角度'),('limits','机械限位 / 速度'),('visible','可见光视场角'),('infrared','红外视场角'),('base','云台底座 XYZ'),('geo','云台仿真经纬高'),('target','无人机 XYZ'),('target_geo','无人机仿真经纬高'),('range','选定镜头 → 无人机'),('camera','选定镜头光心 XYZ'),('bearing','镜头方位 / 仰角'),('api','控制接口')]:
            value=QLabel('未连接');value.setWordWrap(True);value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);form.addRow(title,value);self.values[key]=value
        edit=QPushButton('编辑所选镜头参数 / 视场角…');edit.clicked.connect(self.edit_sensor);form.addRow(edit)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(telemetry);self.tabs.addTab(scroll,'设备数值')
        pointing=QWidget();box=QVBoxLayout(pointing)
        options=QFormLayout();self.sensor=QComboBox();self.sensor.addItem('可见光光轴','visible');self.sensor.addItem('红外光轴','infrared');options.addRow('指向镜头',self.sensor)
        self.target=QComboBox();options.addRow('坐标来源无人机',self.target);box.addLayout(options)
        aim=QPushButton('按该无人机当前坐标指向一次');aim.clicked.connect(self.aim_drone);box.addWidget(aim);self.aim_drone_button=aim
        self.mode=QComboBox();self.mode.addItems(['UE 世界坐标 / 米','WGS84 仿真经纬高']);box.addWidget(self.mode)
        fields=QFormLayout();self.point_fields=[number(-100000,100000,5) for _ in range(3)];self.point_labels=[]
        for title,field in zip(('X / m','Y / m','Z / m'),self.point_fields):
            label=QLabel(title);self.point_labels.append(label);fields.addRow(label,field)
        box.addLayout(fields);self.aim_button=QPushButton('指向输入坐标');self.aim_button.setObjectName('primary');self.aim_button.clicked.connect(self.aim_input);box.addWidget(self.aim_button)
        note=QLabel('这是坐标指向，不是图像跟踪或测距仪。单次提交会退出真值跟踪并保持新朝向；持续跟随需重复提交新坐标。越界会拒绝，保持原姿态。外部SDK支持同样操作。');note.setWordWrap(True);box.addWidget(note);box.addStretch();self.tabs.addTab(pointing,'坐标指向')
        reference=QWidget();refbox=QVBoxLayout(reference);refnote=QLabel('自定义仿真地理基准，不代表 City Sample 的真实位置。经纬度为 WGS84；高度统一为椭球高，不是海拔或离地高。0只是待填写值，保存后才启用。');refnote.setWordWrap(True);refbox.addWidget(refnote)
        refform=QFormLayout();self.latitude=number(-90,90,7,' °');self.longitude=number(-180,180,7,' °');self.height=number(-10000,100000,3,' m')
        for text,field in [('基准纬度',self.latitude),('基准经度',self.longitude),('基准椭球高',self.height)]:refform.addRow(text,field)
        self.origin=[number(-100000,100000,3,' m') for _ in range(3)]
        for axis,field in zip('XYZ',self.origin):refform.addRow('基准 UE '+axis,field)
        self.azimuth=number(0,360,2,' °');refform.addRow('UE +X 相对真北顺时针',self.azimuth);refbox.addLayout(refform)
        anchor=QPushButton('使用当前云台底座作为 UE 基准点');anchor.clicked.connect(self.use_base);refbox.addWidget(anchor)
        save=QPushButton('保存仿真地理基准');save.setObjectName('primary');save.clicked.connect(self.save_reference);refbox.addWidget(save)
        self.reference_path=QLabel('连接场景后显示保存路径');self.reference_path.setWordWrap(True);self.reference_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);refbox.addWidget(self.reference_path);refbox.addStretch()
        area=QScrollArea();area.setWidgetResizable(True);area.setWidget(reference);self.tabs.addTab(area,'仿真地理基准')
        self.status=QLabel('未连接；等待此云台状态。');self.status.setWordWrap(True);root.addWidget(self.status)
        self.sensor.currentIndexChanged.connect(lambda _:self.update_values());self.target.currentIndexChanged.connect(lambda _:self.update_values());self.mode.currentIndexChanged.connect(self.change_mode)
        w.client.state_received.connect(self.update_state);w.client.request_completed.connect(self.completed);w.client.request_failed.connect(self.failed)
        w.client.connection_changed.connect(lambda ready,_:None if ready else self.disconnected())
        self.update_state(w.state);self.controls()

    def change_mode(self,*_):
        geo=self.mode.currentIndex()==1
        for i,field in enumerate(self.point_fields):
            field.setRange(-90 if i==0 and geo else -180 if i==1 and geo else -100000,90 if i==0 and geo else 180 if i==1 and geo else 100000)
            field.setDecimals(7 if geo and i<2 else 3);field.setValue(0)
            self.point_labels[i].setText(('纬度 / °','经度 / °','椭球高 / m')[i] if geo else ('X / m','Y / m','Z / m')[i])
        self.controls()

    def edit_sensor(self):
        from apps.desktop_app.workbench_v3 import show_properties
        self.hide();self.owner.pages.setCurrentIndex(1);show_properties(self.owner,'sensor',self.device_id+'/'+self.sensor.currentData())

    def update_state(self,state):
        if state.get('gimbal_id')!=self.device_id:return
        if self.scene_id!=state.get('scene_id'):
            self.scene_id=state.get('scene_id');self.reference=None
            self.reference_path.setText('基准文件：'+str(self.store.path(self.scene_id)))
            try:self.reference=self.store.load(self.scene_id)
            except (OSError,ValueError,KeyError) as error:self.status.setText('地理基准读取失败：'+str(error))
            if self.reference:
                r=self.reference;self.latitude.setValue(r.latitude_deg);self.longitude.setValue(r.longitude_deg);self.height.setValue(r.ellipsoid_height_m);self.azimuth.setValue(r.x_axis_azimuth_deg)
                for field,value in zip(self.origin,r.world_origin_cm):field.setValue(value/100)
            else:
                for field in (self.latitude,self.longitude,self.height,self.azimuth):field.setValue(0)
                for field,value in zip(self.origin,state.get('gimbal_position_cm',(0,0,0))):field.setValue(value/100)
        self.last=state;self.identity.setText(self.device_id+' · '+str(self.scene_id)+' · '+('自定义仿真基准' if self.reference else '地理基准未设置'))
        selected=self.target.currentData() or self.owner.selected_drone;blocker=QSignalBlocker(self.target);self.target.clear()
        for device in state.get('devices',[]):
            if device['kind']=='drone':self.target.addItem(device['id'],device['id'])
        self.target.setCurrentIndex(max(0,self.target.findData(selected)));del blocker
        self.update_values();self.controls()

    def geo_text(self,position):
        if self.reference is None:return '未设置仿真地理基准'
        lat,lon,h=self.reference.world_to_geodetic(position)
        return f'{lat:.7f}° / {lon:.7f}° / {h:.3f} m（椭球高；仿真）'

    def update_values(self):
        if not self.last:return
        state=self.last;sensors=state.get('sensors',{});sensor=sensors.get(self.sensor.currentData(),{})
        self.values['frame'].setText('UE 世界厘米 → 米；Z为世界高程，未配准时不是海拔。')
        self.values['pose'].setText(f"偏航 {state['yaw_deg']:.3f}° / 俯仰 {state['pitch_deg']:.3f}°（相对底座）")
        self.values['limits'].setText(f"俯仰 {state['pitch_min_deg']:g}～{state['pitch_max_deg']:g}°；偏航±180°；30 / 20°每秒")
        for key in ('visible','infrared'):
            data=sensors.get(key,{})
            self.values[key].setText(f"水平 {data['fov_deg']:.3f}° / 垂直 {data['vertical_fov_deg']:.3f}° · {data['width_px']}×{data['height_px']}" if 'vertical_fov_deg' in data else '等待新版UE回读')
        base=state['gimbal_position_cm'];self.values['base'].setText(position_text(base));self.values['geo'].setText(self.geo_text(base))
        camera=sensor.get('camera_position_cm');self.values['camera'].setText(position_text(camera) if camera else '未提供')
        rotation=sensor.get('camera_rotation_pitch_yaw_roll_deg')
        self.values['bearing'].setText('未提供')
        if rotation:
            self.values['bearing'].setText(f"{(rotation[1]+self.reference.x_axis_azimuth_deg)%360:.3f}° / {rotation[0]:+.3f}°（仿真北向）" if self.reference else f'世界偏航 {rotation[1]:.3f}° / 仰角 {rotation[0]:+.3f}°（北向未设置）')
        drone=next((d for d in state.get('devices',[]) if d['id']==self.target.currentData()),None)
        self.values['target'].setText(position_text(drone['position_cm']) if drone else '未提供')
        self.values['target_geo'].setText(self.geo_text(drone['position_cm']) if drone else '未提供')
        self.values['range'].setText('未提供')
        if drone and camera:
            dx,dy,dz=[(a-b)/100 for a,b in zip(drone['position_cm'],camera)]
            self.values['range'].setText(f'斜距 {math.sqrt(dx*dx+dy*dy+dz*dz):.3f} m / 水平 {math.hypot(dx,dy):.3f} m / 高差 {dz:+.3f} m（几何真值）')
        self.values['api'].setText(f'TCP JSON Lines · {self.owner.client.config.host}:{self.owner.client.config.port} · device_id={self.device_id}')

    def controls(self):
        ready=bool(self.last and self.owner.client.ready and self.last.get('coordinate_pointing_supported') and not self.pending)
        self.aim_button.setEnabled(ready and (self.mode.currentIndex()==0 or self.reference is not None));self.aim_drone_button.setEnabled(ready and self.target.count()>0)

    def use_base(self):
        if self.last:
            for field,value in zip(self.origin,self.last['gimbal_position_cm']):field.setValue(value/100)

    def save_reference(self):
        if not self.last or not self.owner.client.ready:self.status.setText('请先连接并确认当前场景。');return
        try:
            r=GeoReference(self.scene_id,self.latitude.value(),self.longitude.value(),self.height.value(),tuple(f.value()*100 for f in self.origin),self.azimuth.value())
            self.store.save(r);self.reference=r;self.update_state(self.last);self.status.setText('自定义仿真基准已保存；未修改或移动地图，不代表真实测绘配准。')
        except (OSError,ValueError) as error:self.status.setText('保存失败：'+str(error))

    def aim_drone(self):
        if not self.last:return
        drone=next((d for d in self.last['devices'] if d['id']==self.target.currentData()),None)
        if drone:self.submit(drone['position_cm'])

    def aim_input(self):
        try:
            values=[f.value() for f in self.point_fields]
            if self.mode.currentIndex()==1:
                if self.reference is None:raise ValueError('请先保存自定义仿真基准')
                position=self.reference.geodetic_to_world(*values)
            else:position=[v*100 for v in values]
            self.submit(position)
        except ValueError as error:self.status.setText(str(error))

    def submit(self,position):
        if not self.last or not self.owner.client.ready or self.pending:return
        self.owner.clear_gimbal_input()
        self.pending=self.owner.client.request('gimbal.point_at',dict(device_id=self.device_id,scene_id=self.last['scene_id'],run_id=self.last['run_id'],sensor=self.sensor.currentData(),position_cm=position))
        self.status.setText('坐标指向提交中，等待实际回读。');self.controls()

    def completed(self,request,command,payload,state):
        if request!=self.pending:return
        self.pending=None;self.update_state(state);self.status.setText('坐标指向已确认 · 光轴误差 '+str(state['coordinate_pointing']['error_deg'])+'°');self.controls()

    def failed(self,request,command,payload,message):
        if request==self.pending:self.pending=None;self.status.setText('指向失败／未确认：'+message);self.controls()

    def disconnected(self):
        self.last=None;self.pending=None
        for value in self.values.values():value.setText('连接已断开，状态不可用')
        self.status.setText('未连接；位置和角度已失效。');self.controls()


def open_device(w):
    dialog=getattr(w,'gimbal_device_dialog',None)
    if dialog is not None and dialog.device_id!=w.selected_gimbal:dialog.close();dialog.deleteLater();dialog=None
    if dialog is None:w.gimbal_device_dialog=dialog=GimbalDeviceDialog(w)
    dialog.show();dialog.raise_()
