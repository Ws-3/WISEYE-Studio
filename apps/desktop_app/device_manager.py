"""Scene device drafts and independent runtime selection."""
import copy
from PySide6.QtCore import Qt,QSignalBlocker,QTimer
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QComboBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QTreeWidgetItem,QCheckBox
from core.config import ROOT
from core.devices import DeviceStore,MODELS

class DeviceManager(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.store=DeviceStore(ROOT);self.scene=window.scenes.currentData();self.data=self.store.load(self.scene)
        from core.live_devices import from_state
        if window.client.ready and window.state.get('scene_id')==self.scene['id']:self.data=from_state(window.state)
        self.live_snapshot=copy.deepcopy(self.data);self.live_revision=window.state.get('fleet_revision',0);self.pending_live=None
        self.live_timer=QTimer(self);self.live_timer.setSingleShot(True);self.live_timer.setInterval(450);self.live_timer.timeout.connect(self.apply_live)
        self.live_enabled=QCheckBox('实时应用到当前场景');self.live_enabled.setChecked(window.client.ready and window.air_client.ready and window.state.get('fleet_live_edit_supported',False))
        self.live_enabled.toggled.connect(lambda enabled:self.schedule_live() if enabled else self.live_timer.stop())
        window.air_client.completed.connect(self.live_completed);window.air_client.failed.connect(self.live_failed)
        self.setWindowTitle('场景设备 · 实时编辑与初始配置');self.resize(1120,650)
        box=QVBoxLayout(self);box.setContentsMargins(20,18,20,18);box.setSpacing(14)
        heading=QLabel('场景设备库');heading.setObjectName('title');box.addWidget(heading)
        text=QLabel('开启实时应用可直接增删与修改设备；保存为初始配置只影响下次加载。每类最多4个，默认ID保留。');text.setWordWrap(True);box.addWidget(text)
        self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels(['实例 ID','类型','型号','名称','X / m','Y / m','Z / m','朝向 / °','跟踪目标',''])
        self.table.setAlternatingRowColors(True);self.table.setShowGrid(False);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.table.horizontalHeader().setStretchLastSection(True);box.addWidget(self.table,1)
        row=QHBoxLayout()
        for text,callback in [('新增无人机',lambda:self.add('drone')),('新增云台',lambda:self.add('gimbal')),('复制选中实例',self.duplicate),('删除选中实例',self.remove),('保存设备配置',self.save),('保存并加载场景',self.reload)]:
            button=QPushButton(text);button.setObjectName('primary' if text=='保存并加载场景' else 'danger' if text=='删除选中实例' else '');button.clicked.connect(callback);row.addWidget(button)
        box.addLayout(row);self.message=QLabel('位置为UE世界坐标，Z向上。当前场景可实时修改，初始配置单独保存。');self.message.setWordWrap(True);box.addWidget(self.message);self.render()
        self.table.itemChanged.connect(lambda *_:self.schedule_live())

        self.saved_snapshot=copy.deepcopy(self.collect())

    def render(self):
        self.table.setRowCount(0)
        for item in self.data['devices']:
            row=self.table.rowCount();self.table.insertRow(row)
            for col,value in [(0,item['id']),(1,'无人机' if item['kind']=='drone' else '云台'),(3,item['name'])]+[(i+4,n/100) for i,n in enumerate(item['position_cm'])]+[(7,item['rotation_deg'][1])]:
                cell=QTableWidgetItem(str(value))
                if col in (0,1):cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row,col,cell)
            model=QComboBox()
            for ident,template in MODELS.items():
                if template['kind']==item['kind']:model.addItem(template['name'],ident)
            model.setCurrentIndex(model.findData(item['model_id']));self.table.setCellWidget(row,2,model);model.currentIndexChanged.connect(lambda *_:self.schedule_live())
            target=QComboBox()
            for drone in self.data['devices']:
                if drone['kind']=='drone':target.addItem(drone['id'],drone['id'])
            target.setCurrentIndex(max(0,target.findData(item.get('tracking_target'))));target.setEnabled(item['kind']=='gimbal');self.table.setCellWidget(row,8,target);target.currentIndexChanged.connect(lambda *_:self.schedule_live())

    def collect(self):
        data=copy.deepcopy(self.data)
        for row,item in enumerate(data['devices']):
            try:
                item['name']=self.table.item(row,3).text().strip();item['model_id']=self.table.cellWidget(row,2).currentData()
                item['position_cm']=[float(self.table.item(row,col).text())*100 for col in (4,5,6)]
                item['rotation_deg']=[0,float(self.table.item(row,7).text()),0]
                if item['kind']=='gimbal':item['tracking_target']=self.table.cellWidget(row,8).currentData()
            except (ValueError,AttributeError):raise ValueError('请填写完整、有效的坐标与偏航角')
        from core.devices import validate_devices
        return validate_devices(data,self.scene['id'])

    def add(self,kind,source=None):
        try:self.data=self.collect()
        except ValueError as exc:self.message.setText(str(exc));return
        group=[i for i in self.data['devices'] if i['kind']==kind]
        if len(group)>=4:self.message.setText('每类最多 4 个实例');return
        prefix='uav' if kind=='drone' else 'ptz';ids={i['id'] for i in self.data['devices']};ident=next(f'{prefix}-{n:02}' for n in range(2,100) if f'{prefix}-{n:02}' not in ids)
        item=copy.deepcopy(source or group[-1]);item['id']=ident;item['name']=ident;item['position_cm'][0 if kind=='drone' else 1]+=500
        self.data['devices'].append(item);self.render();self.table.selectRow(self.table.rowCount()-1);self.schedule_live()

    def duplicate(self):
        try:data=self.collect();row=self.table.currentRow()
        except ValueError as exc:self.message.setText(str(exc));return
        if row>=0:self.add(data['devices'][row]['kind'],data['devices'][row])

    def remove(self):
        try:self.data=self.collect()
        except ValueError as exc:self.message.setText(str(exc));return
        row=self.table.currentRow()
        if row<0:return
        item=self.data['devices'][row]
        if item['id'] in ('uav-01','ptz-01'):self.message.setText('默认实例保留；可修改其型号和位置');return
        self.data['devices'].pop(row)
        for other in self.data['devices']:
            if other.get('tracking_target')==item['id']:other['tracking_target']='uav-01'
        self.render();self.message.setText('实例已从编辑列表删除；引用它的跟踪目标已改为 uav-01。');self.schedule_live()

    def save(self):
        try:
            self.data=self.collect();self.store.save(self.data)
            self.saved_snapshot=copy.deepcopy(self.data)
            self.window.arrangement.refresh_devices()
            self.message.setText('已保存为下次启动的初始配置；保存本身不改变当前场景。');return True
        except (ValueError,OSError) as exc:self.message.setText('保存失败：'+str(exc));return False

    def reload(self):
        self.apply_live(force=True)

    def schedule_live(self):
        if self.live_enabled.isChecked():self.live_timer.start()

    def apply_live(self,force=False):
        if self.pending_live is not None:return
        w=self.window
        if not w.client.ready or not w.air_client.ready or w.state.get('scene_id')!=self.scene['id']:
            self.message.setText('未连接当前场景；编辑保留在草稿，可保存为初始配置。');return
        try:
            from core.live_devices import changes
            data=self.collect();patch=changes(self.live_snapshot,data)
            if not patch:self.message.setText('当前场景已是所编辑的设备配置。');return
            self.pending_live=copy.deepcopy(data);self.pending_patch=patch
            w.air_client.request('fleet.apply',dict(scene_id=self.scene['id'],run_id=w.state['run_id'],expected_revision=self.live_revision,changes=patch))
            self.message.setText('正在应用到当前场景，不重载地图…')
        except (ValueError,OSError) as error:self.pending_live=None;self.message.setText(str(error))

    def live_completed(self,command,state):
        if command!='fleet.apply' or self.pending_live is None:return
        self.live_snapshot=self.pending_live;self.pending_live=None;self.live_revision=state['fleet_revision']
        self.message.setText('已实时应用；如需下次启动保留，请保存为初始配置。')
        self.window.client.request('sim.get_state')
        page=self.window.arrangement
        for item in getattr(self,'pending_patch',[]):
            if item['action']=='remove' or 'position_cm' in item or 'rotation_deg' in item:page.dirty_positions.discard(page.coordinate_key(item['id']))
        page.refresh_devices(dict(self.window.state,devices=state['live_devices']))
        try:
            if self.collect()!=self.live_snapshot:self.schedule_live()
        except ValueError:pass

    def live_failed(self,command,message):
        if command!='fleet.apply' or self.pending_live is None:return
        self.pending_live=None;self.live_timer.stop();self.message.setText('实时应用失败：'+message)

class FleetSelection(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.signature=None
        from apps.desktop_app.ui.components import ChoiceInput
        layout=QFormLayout(self);layout.setContentsMargins(0,0,0,0)
        self.drone=ChoiceInput();self.gimbal=ChoiceInput()
        layout.addRow('驾驶',self.drone);layout.addRow('云台',self.gimbal)
        self.drone.activated.connect(lambda _:self.select('drone',self.drone.currentData()));self.gimbal.activated.connect(lambda _:self.select('gimbal',self.gimbal.currentData()))
        self.sensor_drafts={}

    def manage(self):
        if hasattr(self.window,'device_page'):
            self.window.pages.setCurrentIndex(4);return
        try:dialog=DeviceManager(self.window);dialog.exec()
        except (ValueError,OSError) as exc:self.window.log('设备配置读取失败：'+str(exc))

    def inventory(self,state):
        devices=state.get('devices',[]);signature=tuple((d['id'],d['kind'],d['model_id'],d.get('name')) for d in devices)
        if signature==self.signature:return
        self.signature=signature;w=self.window
        if hasattr(w,'arrangement') and state.get('scene_id')==(w.scenes.currentData() or {}).get('id'):
            w.arrangement.refresh_devices(state)
        for kind,combo,selected in [('drone',self.drone,w.selected_drone),('gimbal',self.gimbal,w.selected_gimbal)]:
            blocker=QSignalBlocker(combo);combo.clear()
            for d in devices:
                if d['kind']==kind:combo.addItem(f"{d['id']} · {MODELS.get(d['model_id'],{}).get('name',d['model_id'])}",d['id'])
            combo.setCurrentIndex(max(0,combo.findData(selected)));del blocker
            if combo.currentData() and combo.currentData()!=selected:self.select(kind,combo.currentData())
        blocker=QSignalBlocker(w.object_tree);w.object_tree.clear();root=QTreeWidgetItem(w.object_tree,['当前场景'])
        for d in devices:
            name=d.get('name',d['id'])
            node=QTreeWidgetItem(root,[d['id'] if name==d['id'] else name+' · '+d['id']]);node.setToolTip(0,name+' / '+d['id']);node.setData(0,Qt.ItemDataRole.UserRole,(d['kind'],d['id']))
            if d['kind']=='gimbal':
                for sensor,title in [('visible','可见光'),('infrared','红外'),('lidar','激光雷达'),('event','事件相机')]:
                    child=QTreeWidgetItem(node,[title]);child.setData(0,Qt.ItemDataRole.UserRole,('sensor',d['id']+'/'+sensor))
            elif d['kind']=='drone' and 'aerial' in d:
                child=QTreeWidgetItem(node,['机载可见光']);child.setData(0,Qt.ItemDataRole.UserRole,('sensor',d['id']+'/aerial'))
                ir=QTreeWidgetItem(node,['机载红外']);ir.setData(0,Qt.ItemDataRole.UserRole,('sensor',d['id']+'/aerial_infrared'))
            node.setExpanded(True)
        root.setExpanded(True);del blocker
        blocker=QSignalBlocker(w.tracking_target);w.tracking_target.clear()
        for d in devices:
            if d['kind']=='drone':w.tracking_target.addItem(d['id'],d['id'])
        del blocker

    def select(self,kind,ident):
        w=self.window
        if not ident:return
        if kind=='drone':
            if ident==w.selected_drone:return
            w.manual_keys.clear();w.stop_manual_input()
            if getattr(w,'route_editor',None):w.route_editor.start_after_upload=False
            w.selected_drone=ident;w.air_client.device_id=ident;w.air_state={}
            w.client.request('input.select_drone',{'drone_id':ident});w.air_client.request('sim.get_state')
        else:
            if ident==w.selected_gimbal:return
            w.clear_gimbal_input()
            w.selected_gimbal=ident;w.client.device_id=ident;w.device_switching=True
            w.client.request('input.select_gimbal',{'gimbal_id':ident});w.client.request('sim.get_state')
        for combo,value in [(self.drone,w.selected_drone),(self.gimbal,w.selected_gimbal)]:
            blocker=QSignalBlocker(combo);combo.setCurrentIndex(combo.findData(value));del blocker
        w.statusBar().showMessage(f'驾驶 {w.selected_drone} · 云台 {w.selected_gimbal}')
        from apps.desktop_app.workbench_v3 import refresh_inspector,show_properties
        if w.inspectors.currentIndex()==(0 if kind=='drone' else 1):show_properties(w,kind,ident)
        else:refresh_inspector(w)
