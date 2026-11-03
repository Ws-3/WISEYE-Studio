from PySide6.QtCore import QSignalBlocker, Qt, QPointF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QFrame, QScrollArea
from PySide6.QtGui import QPainter, QColor, QPen
from apps.desktop_app.ui.components import NumberInput
from apps.desktop_app.ui.icons import icon
from core.config import ROOT
from core.layouts import LayoutStore


class ArrangementPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.store = LayoutStore(ROOT)
        self.device_specs = []
        self.dirty_positions = set()
        outer = QVBoxLayout(self); outer.setContentsMargins(0,12,0,0); outer.setSpacing(12)
        area = QScrollArea(); area.setWidgetResizable(True)
        body = QWidget(); area.setWidget(body); outer.addWidget(area,1)
        layout = QVBoxLayout(body); layout.setContentsMargins(0,0,8,0); layout.setSpacing(16)
        heading=QHBoxLayout()
        titles=QVBoxLayout();titles.setSpacing(4)
        titles.addWidget(window._label('构建你的仿真场景', 'title'))
        titles.addWidget(window._label('选择环境，布置设备，然后加载开始仿真。'))
        heading.addLayout(titles);heading.addStretch()
        manage=window._button('管理全部设备',lambda:window.fleet_selection.manage(),control=False)
        manage.setIcon(icon('settings'));heading.addWidget(manage);layout.addLayout(heading)

        scene_card,scene_layout=self.card('01  /  ENVIRONMENT','仿真环境')
        row=QHBoxLayout();window.scenes = QComboBox();window.scenes.setMinimumWidth(250)
        window.refresh_scenes();row.addWidget(window.scenes,1)
        row.addWidget(window._button('地图资源管理',window.manage_scenes,control=False));scene_layout.addLayout(row)
        self.scene_note=window._label('');self.scene_note.setWordWrap(True);scene_layout.addWidget(self.scene_note)
        layout.addWidget(scene_card)

        self.columns=QGridLayout();self.columns.setSpacing(16);layout.addLayout(self.columns)
        self.position_card,positions=self.card('02  /  PLACEMENT','设备初始位置')
        note=window._label('跟随当前场景的设备列表；坐标与表面取点按设备独立编辑。');note.setWordWrap(True);positions.addWidget(note)
        self.coordinates = {}
        self.yaw_fields = {}
        self.map=PlacementPreview(self);positions.addWidget(self.map)
        grid=QGridLayout();self.position_grid=grid;grid.setHorizontalSpacing(10);grid.setVerticalSpacing(10)
        for col,label in enumerate(['设备','X / m','Y / m','Z / m']):grid.addWidget(window._label(label,'section'),0,col)
        for row,(key,title) in enumerate([('flight_origin_cm','无人机 · 01'),('gimbal_location_cm','云台 · 01')],1):
            grid.addWidget(window._label(title),row,0);self.coordinates[key]=[]
            for col in range(3):
                spin=NumberInput(-100000,100000,'',3,.1);spin.setMinimumWidth(85)
                self.coordinates[key].append(spin);grid.addWidget(spin,row,col+1)
                spin.valueChanged.connect(lambda _:self.map.update())
        positions.addLayout(grid)
        hint=window._label('世界坐标 · 单位米 · Z 轴向上。示意图展示全部设备的草稿位置。','hint');hint.setWordWrap(True);positions.addWidget(hint);positions.addStretch()

        self.tools_card,tools_layout=self.card('03  /  PRESETS & SURFACE','位置预设与表面取点')
        from apps.desktop_app.placement_controls import ArrangementTools
        self.tools = ArrangementTools(self);tools_layout.addWidget(self.tools);tools_layout.addStretch()
        self.columns.addWidget(self.position_card,0,0);self.columns.addWidget(self.tools_card,0,1)
        self.columns.setColumnStretch(0,1);self.columns.setColumnStretch(1,1)
        layout.addStretch()
        footer=QFrame();footer.setObjectName('arrangeFooter');foot=QVBoxLayout(footer);foot.setContentsMargins(14,10,14,10)
        self.message=window._label('读取初始布置…');self.message.setWordWrap(True);foot.addWidget(self.message)
        actions=QHBoxLayout()
        actions.addWidget(window._button('重新读取',self.load,control=False));actions.addStretch()
        actions.addWidget(window._button('保存初始布置',self.save,control=False))
        window.switch_button=window._button('加载场景',window.switch_scene,True)
        window.switch_button.setToolTip('加载所选场景及已保存布置；需要所有无人机已降落。')
        window.switch_button.setIcon(icon('scene'));actions.addWidget(window.switch_button);foot.addLayout(actions)
        outer.addWidget(footer)
        window.scenes.currentIndexChanged.connect(self.load)
        self.load()

    def card(self, eyebrow, title):
        frame=QFrame();frame.setObjectName('arrangeCard')
        layout=QVBoxLayout(frame);layout.setContentsMargins(20,16,20,18);layout.setSpacing(12)
        layout.addWidget(self.window._label(eyebrow,'section'))
        layout.addWidget(self.window._label(title,'value'))
        return frame,layout

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'columns') and not getattr(self,'_v4_layout',False):
            stacked=self.width()<1150
            self.columns.addWidget(self.tools_card,1 if stacked else 0,0 if stacked else 1)
            self.columns.setColumnStretch(1,0 if stacked else 1)

    def load(self, *_):
        scene = self.window.scenes.currentData()
        if not scene:
            return
        self.scene_note.setText(f"{scene['name']} · 当前场景可实时调整位置与朝向；保存初始布置用于下次启动。新增/删除设备或切换地图仍需加载场景。")
        try:
            data = self.store.load(scene)
            from core.devices import DeviceStore
            fleet_store=DeviceStore(ROOT)
            fleet=fleet_store.load(scene)
            self.sync_devices(fleet['devices'],preserve=False)
            for item in fleet['devices']:data[self.coordinate_key(item['id'])]=item['position_cm']
            for key, widgets in self.coordinates.items():
                for value, spin in zip(data[key], widgets):
                    blocker = QSignalBlocker(spin)
                    spin.setValue(value/100)
                    del blocker
            self.map.update()
            self.dirty_positions.clear()
            self.tools.refresh()
            self.message.setText(f"{scene['name']} · 已读取保存的位置。")
        except (ValueError, OSError, TypeError) as exc:
            self.message.setText(f'读取失败：{exc}')

    @staticmethod
    def coordinate_key(ident):
        return {'uav-01':'flight_origin_cm','ptz-01':'gimbal_location_cm'}.get(ident,ident)

    def position_edited(self,key):
        self.dirty_positions.add(key)
        self.map.update()
        if hasattr(self,'tools'):self.tools.draft_changed()
        if hasattr(self,'tools'):self.tools.schedule_apply(key)

    def sync_devices(self,devices,preserve=True):
        old={key:[v.value()*100 for v in fields] for key,fields in self.coordinates.items()}
        if hasattr(self,'tools'):self.tools.cancel_pending()
        while self.position_grid.count():
            item=self.position_grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        old_yaw={key:field.value() for key,field in self.yaw_fields.items()}
        self.coordinates={};self.yaw_fields={};self.device_specs=list(devices)
        self.dirty_positions.intersection_update(self.coordinate_key(d['id']) for d in devices)
        v4=getattr(self,'_v4_layout',False)
        self.v4_field_groups={}
        if not v4:
            for col,label in enumerate(['设备','X / m','Y / m','Z / m','朝向 / °']):
                self.position_grid.addWidget(self.window._label(label,'section'),0,col)
        for row,device in enumerate(devices,1):
            key=self.coordinate_key(device['id']);group=[];self.v4_field_groups[key]=group
            values=old[key] if preserve and key in self.dirty_positions and key in old else device['position_cm']
            if not v4:self.position_grid.addWidget(self.window._label(device['id']),row,0)
            self.coordinates[key]=[]
            for col,value in enumerate(values,1):
                field=NumberInput(-100000,100000,'m' if v4 else '',3,.1);field.setMinimumWidth(85);field.setValue(value/100)
                field.valueChanged.connect(lambda _,k=key:self.position_edited(k))
                self.coordinates[key].append(field)
                if v4:
                    label=self.window._label(('X','Y','Z')[col-1]);r=(row-1)*4+col-1
                    self.position_grid.addWidget(label,r,0);self.position_grid.addWidget(field,r,1);group.extend([label,field])
                else:self.position_grid.addWidget(field,row,col)
            yaw=old_yaw[key] if preserve and key in self.dirty_positions and key in old_yaw else device['rotation_deg'][1]
            field=NumberInput(-180,180,'°' if v4 else '',1,1);field.setValue(yaw);field.setMinimumWidth(70)
            field.valueChanged.connect(lambda _,k=key:self.position_edited(k));self.yaw_fields[key]=field
            if v4:
                label=self.window._label('Yaw');r=(row-1)*4+3
                self.position_grid.addWidget(label,r,0);self.position_grid.addWidget(field,r,1);group.extend([label,field])
            else:self.position_grid.addWidget(field,row,4)
        if hasattr(self,'tools'):self.tools.refresh_devices()
        if v4:
            from apps.desktop_app.arrangement_v4 import refresh_devices
            refresh_devices(self)
        self.map.update()

    def refresh_devices(self):
        scene=self.window.scenes.currentData()
        if scene:
            from core.devices import DeviceStore
            self.sync_devices(DeviceStore(ROOT).load(scene)['devices'])

    def save(self):
        scene = self.window.scenes.currentData()
        if not scene:
            return
        data = dict(version=1, scene_id=scene['id'])
        for key, widgets in self.coordinates.items():
            data[key] = [spin.value()*100 for spin in widgets]
        data['headings_deg']={key:field.value() for key,field in self.yaw_fields.items()}
        try:
            from core.devices import DeviceStore
            fleet_store=DeviceStore(ROOT)
            fleet=fleet_store.load(scene)
            for device in fleet['devices']:
                key=self.coordinate_key(device['id'])
                if key in self.dirty_positions and key in data:
                    device['position_cm']=data[key]
                    device['rotation_deg'][1]=self.yaw_fields[key].value()
            fleet_store.save(fleet)
            for device in fleet['devices']:data[self.coordinate_key(device['id'])]=device['position_cm']
            path=self.store.save(data)
            self.dirty_positions.clear()
            self.message.setText('初始布置已保存，供下次启动使用；当前设备位置以实时应用确认结果为准，无需重载场景。')
            self.window.log(f'初始布置已保存：{path}')
        except (ValueError, OSError, TypeError) as exc:
            self.message.setText(f'保存失败：{exc}')


class PlacementPreview(QWidget):
    """Read-only plan view of all configured position drafts."""
    def __init__(self,page):
        super().__init__();self.page=page;self.setMinimumHeight(170);self.setMaximumHeight(220)
        self.setToolTip('全部设备草稿俯视示意，不包含地形或碰撞；X 向右、Y 向上。')

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor('#121923'))
        painter.setPen(QPen(QColor('#253142'),1))
        for x in range(0,self.width(),24):painter.drawLine(x,0,x,self.height())
        for y in range(0,self.height(),24):painter.drawLine(0,y,self.width(),y)
        points=[[v.value() for v in values[:2]] for values in self.page.coordinates.values()]
        if points:
            cx=(max(v[0] for v in points)+min(v[0] for v in points))/2;cy=(max(v[1] for v in points)+min(v[1] for v in points))/2
            scale=min((self.width()-130)/max(20,max(v[0] for v in points)-min(v[0] for v in points)),(self.height()-85)/max(20,max(v[1] for v in points)-min(v[1] for v in points)))
            pixels=[QPointF(self.width()/2+(x-cx)*scale,self.height()/2-(y-cy)*scale) for x,y in points]
            specs=self.page.device_specs or [dict(id='uav-01',kind='drone'),dict(id='ptz-01',kind='gimbal')]
            for i,(point,device) in enumerate(zip(pixels,specs)):
                color='#70abff' if device['kind']=='drone' else '#5ed2bd';label=device['id']
                painter.setBrush(QColor(color));painter.setPen(Qt.PenStyle.NoPen);painter.drawEllipse(point,5,5)
                painter.setPen(QColor(color));painter.drawText(point+QPointF(10,-10 if i==0 else 19),label)
        painter.setPen(QColor('#7d91ac'));painter.drawText(12,20,'DRAFT / XY');painter.drawText(12,self.height()-12,'X →   Y ↑   ·   自动缩放')
        painter.end()
