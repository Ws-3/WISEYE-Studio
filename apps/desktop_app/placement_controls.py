"""Named layout library and asynchronous UE surface selection for a position draft."""
import uuid
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QDoubleSpinBox


class ArrangementTools(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page, self.window = page, page.window
        self.pending = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.window._label('布置预设','section'))
        row = QHBoxLayout()
        self.presets, self.name = QComboBox(), QLineEdit()
        self.presets.setMinimumWidth(200)
        self.name.setPlaceholderText('预设名称，例如：沙漠近距离观察')
        self.name.setMaxLength(80)
        row.addWidget(self.presets,1)
        row.addWidget(self.name,1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(self.window._button('另存为新预设', lambda:self.save_named(False), control=False))
        self.update_button = self.window._button('更新所选预设', lambda:self.save_named(True), control=False)
        row.addWidget(self.update_button)
        layout.addLayout(row)
        layout.addSpacing(8)
        layout.addWidget(self.window._label('表面取点','section'))
        row = QHBoxLayout()
        from apps.desktop_app.ui.components import ChoiceInput, NumberInput
        self.device, self.clearance = ChoiceInput(), NumberInput(0,10,'m',3,.05)
        self.clearance.setRange(0,10)
        self.clearance.setDecimals(3)
        self.clearance.setValue(.25)
        self.clearance.setSuffix(' m')
        row.addWidget(self.device)
        row.addWidget(self.window._label('距表面高度'))
        row.addWidget(self.clearance)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.pick = self.window._button('到 UE 点击放置', lambda:self.request('placement.begin'), control=False)
        self.snap = self.window._button('当前 X/Y 贴合表面', lambda:self.request('placement.snap'), control=False)
        self.cancel = self.window._button('取消取点', lambda:self.cancel_pending(include_remote=True), control=False)
        for button in (self.pick,self.snap,self.cancel):
            row.addWidget(button)
        layout.addLayout(row)
        note = self.window._label('先用 UE 自由观察找到位置，再启用取点。左键选地面，右键取消。无人机默认留 0.25 m 给物理机体；云台校正底座高度。取点只改草稿，保存并加载场景后才移动设备。')
        note.setObjectName('hint')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.presets.activated.connect(self.select_preset)
        self.device.currentIndexChanged.connect(self.device_changed)
        for fields in page.coordinates.values():
            for field in fields:
                field.valueChanged.connect(self.draft_changed)
        self.refresh()
        self.disconnected()

    def scene_id(self):
        return (self.window.scenes.currentData() or {}).get('id')

    def draft(self):
        return dict(version=1, scene_id=self.scene_id(), **{
            key:[field.value()*100 for field in fields] for key,fields in self.page.coordinates.items()})

    def set_positions(self, data):
        for key, fields in self.page.coordinates.items():
            if key not in data:continue
            changed=any(abs(field.value()*100-value)>1e-6 for field,value in zip(fields,data[key]))
            for value, field in zip(data[key],fields):
                blocker = QSignalBlocker(field)
                field.setValue(value/100)
                del blocker
            if changed:self.page.dirty_positions.add(key)

        self.page.map.update()

    def refresh(self, select=None):
        self.cancel_pending()
        self.refresh_devices()
        blocker = QSignalBlocker(self.presets)
        self.presets.clear()
        self.presets.addItem('当前场景初始布置', None)
        if self.scene_id():
            items, errors = self.page.store.list_presets(self.scene_id())
            for item in items:
                self.presets.addItem(item['name'],item['preset_id'])
            if select:
                self.presets.setCurrentIndex(self.presets.findData(select))
            if errors:
                self.window.log('部分预设未读取：'+'；'.join(errors))
        del blocker
        self.update_button.setEnabled(self.presets.currentData() is not None)
        self.update_connection(self.window.state)

    def select_preset(self, *_):
        self.cancel_pending()
        ident = self.presets.currentData()
        if not ident:
            self.page.load()
            return
        try:
            data = self.page.store.load_preset(self.scene_id(),ident)
            self.set_positions(data)
            self.name.setText(data['name'])
            self.update_button.setEnabled(True)
            self.page.message.setText('已读取预设到草稿。保存初始布置并加载场景后生效。')
        except (ValueError,OSError,TypeError) as exc:
            self.page.message.setText('读取预设失败：'+str(exc))

    def save_named(self, update):
        try:
            ident = self.presets.currentData() if update else None
            if update and not ident:
                raise ValueError('请先选择需要更新的命名预设')
            data = self.page.store.save_preset(self.draft(),self.name.text(),ident)
            self.refresh(data['preset_id'])
            self.page.message.setText(f"预设“{data['name']}”已保存；场景初始布置仍需单独保存后加载。")
        except (ValueError,OSError,TypeError) as exc:
            self.page.message.setText('保存预设失败：'+str(exc))

    def device_changed(self, *_):
        self.cancel_pending()
        value=self.device.currentData()
        self.clearance.setValue(.25 if value and value[0].startswith('uav-') else 0)

    def refresh_devices(self):
        previous=self.device.currentData()
        blocker=QSignalBlocker(self.device);self.device.clear()
        for item in self.page.device_specs:
            title=('无人机' if item['kind']=='drone' else '云台')+' · '+item['id']+' · '+item['name']
            self.device.addItem(title,(item['id'],self.page.coordinate_key(item['id'])))
        index=next((i for i in range(self.device.count()) if self.device.itemData(i)==previous),0)
        self.device.setCurrentIndex(index);del blocker
        self.device_changed()

    def draft_changed(self, *_):
        self.cancel_pending()
        self.page.message.setText('草稿坐标已修改，尚未保存；当前设备没有移动。')

    def request(self, command):
        if not self.window.client.ready or self.window.state.get('scene_id') != self.scene_id():
            self.page.message.setText('请连接 UE，并选择与当前运行一致的场景。')
            return
        if not self.device.currentData():
            self.page.message.setText('请先选择设备。')
            return
        device,key = self.device.currentData()
        if device not in {d['id'] for d in self.window.state.get('devices',[])}:
            self.page.message.setText('该设备尚未加载到 UE。请保存设备配置并加载场景后取点。')
            return
        self.window.manual_keys.clear()
        self.window.stop_manual_input()
        token = uuid.uuid4().hex
        self.pending = dict(token=token,key=key,device_id=device,run_id=self.window.state.get('run_id'),scene_id=self.scene_id())
        payload = dict(scene_id=self.scene_id(), device_id=device,request_token=token,clearance_cm=self.clearance.value()*100)
        if command.endswith('snap'):
            payload['position_cm'] = self.draft()[key]
        self.window.command(command,payload)
        self.update_connection(self.window.state)
        self.page.message.setText('等待表面查询…' if command.endswith('snap') else '请到 UE 点击地面；右键取消，45 秒超时自动退出。')

    def cancel_pending(self, *_, include_remote=False):
        pending,self.pending = self.pending,None
        if pending is None and include_remote:
            remote=self.window.state.get('placement',{})
            if remote.get('active') and self.window.state.get('scene_id')==self.scene_id():
                pending=dict(token=remote['request_token'],scene_id=self.scene_id())
        if pending and self.window.client.ready:
            self.window.command('placement.cancel',dict(scene_id=pending['scene_id'],request_token=pending['token']))
            self.window.client.socket.flush()
        if pending:
            self.page.message.setText('取点已取消；草稿未改变。')
        if hasattr(self,'cancel'):
            self.cancel.setEnabled(False)

    def update_connection(self,state):
        online = self.window.client.ready and state.get('scene_id') == self.scene_id()
        busy=bool(self.pending) or state.get('placement',{}).get('active',False)
        for button in (self.pick,self.snap):
            button.setEnabled(online and not busy and self.device.currentData() is not None)
        self.cancel.setEnabled(online and busy)

    def apply_state(self,state):
        if self.pending and (state.get('run_id')!=self.pending['run_id'] or state.get('scene_id')!=self.pending['scene_id']):
            self.pending=None
            self.page.message.setText('运行场景已改变，旧取点结果已丢弃。')
        result=state.get('placement',{})
        if self.pending and result.get('request_token')==self.pending['token'] and result.get('device_id')==self.pending['device_id']:
            if result.get('has_result') and len(result.get('position_cm',[]))==3:
                key=self.pending['key']
                self.pending=None
                values=self.draft()
                values[key]=result['position_cm']
                self.set_positions(values)
                self.page.message.setText('表面位置已写入草稿。请保存初始布置，再加载场景生效。')
            elif not result.get('active') and result.get('error'):
                self.pending=None
                self.page.message.setText('取点已取消或超时；草稿未改变。')
        self.update_connection(state)

    def disconnected(self):
        self.pending=None
        for button in (self.pick,self.snap,self.cancel):
            button.setEnabled(False)

    def failed(self,command,message):
        if command.startswith('placement.') and command!='placement.cancel':
            self.pending=None
            translations={'No static surface hit':'没有找到可用表面，请调整 X/Y 或检查场景表面是否启用碰撞。',
                          'Surface too steep':'该表面过陡，请选择地面、平台等朝上的表面。'}
            message=next((text for prefix,text in translations.items() if message.startswith(prefix)),message)
            self.page.message.setText('表面查询失败：'+message)
            self.update_connection(self.window.state)
