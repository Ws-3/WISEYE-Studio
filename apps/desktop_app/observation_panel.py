"""Addressed aerial cameras and map-native ambient population controls."""
from PySide6.QtCore import Qt,QSignalBlocker,QTimer
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QComboBox,QCheckBox,QDoubleSpinBox


def save_aerial_frame(window,device,sensor=None):
    from PySide6.QtWidgets import QFileDialog
    if sensor is None:
        mode=getattr(getattr(window,'mission_workspace',None),'modality',None)
        sensor=mode.currentData() if mode and mode.currentData()!='both' else 'aerial'
    key=device+'/'+sensor;gallery=window.gallery
    if key in gallery.messages or key not in gallery.frames or not window.client.ready:return
    path,_=QFileDialog.getSaveFileName(window,'保存航拍原始帧',device+'_'+sensor+'.png','PNG (*.png)')
    if path:window.log(('已保存：' if gallery.frames[key].save(path,'PNG') else '保存失败：')+path)


def show_aerial(window,device):
    gallery=window.gallery;key=device+'/aerial'
    if key not in gallery.sources:gallery.add_source(key,replace=gallery.sources[0] if len(gallery.sources)>=6 else None)
    if key in gallery.sources:
        gallery.sources.remove(key);gallery.sources.insert(0,key);gallery.mode='custom';gallery.expanded=None
        gallery.layout_choice.setCurrentIndex(3);gallery.arrange();window.pages.setCurrentIndex(1)


def open_aerial(window,device=None):
    if hasattr(window,'mission_workspace'):
        window.mission_workspace.open_aerial(device)
        return
    dialog=getattr(window,'aerial_dialog',None)
    if dialog is None:
        dialog=ObservationDialog(window,True);window.aerial_dialog=dialog
    if device:
        index=dialog.device.findData(device)
        if index>=0:dialog.device.setCurrentIndex(index)
    dialog.show();dialog.raise_();dialog.activateWindow();dialog.load()


def open_population(window):
    dialog=getattr(window,'population_dialog',None)
    if dialog is None:
        dialog=ObservationDialog(window,False);window.population_dialog=dialog
    dialog.show();dialog.raise_();dialog.activateWindow();dialog.load()


class ObservationDialog(QDialog):
    def __init__(self,window,aerial,embedded=False):
        super().__init__(window);self.window=window;self.aerial=aerial;self.pending=None;self.run=None;self.loading=True;self.dirty=False;self.valid=False
        self.embedded=embedded
        self.focus_supported=False
        if embedded:self.setWindowFlags(Qt.WindowType.Widget)
        self.configuring=False;self.aim_queued=False
        self.aim_timer=QTimer(self);self.aim_timer.setSingleShot(True);self.aim_timer.setInterval(80);self.aim_timer.timeout.connect(self.flush_aim)
        self.setWindowTitle('无人机航拍' if aerial else '车辆与行人');self.resize(480,420)
        layout=QVBoxLayout(self);layout.setContentsMargins(4,4,4,4);form=QFormLayout();layout.addLayout(form);self.fields={}
        if embedded:form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        if aerial:
            self.device=QComboBox();form.addRow('无人机',self.device)
            self.refresh_devices(window.state);self.device.currentIndexChanged.connect(self.load)
            self.check(form,'enabled','启用机载可见光');self.check(form,'ir_enabled','启用机载红外');self.check(form,'ir_black_hot','红外黑热显示');self.check(form,'stabilized','稳定云台（保持地平线）')
            focus=QComboBox()
            for title,value in [('自动对焦','auto'),('手动距离','manual'),('无穷远','infinity'),('关闭景深','off')]:focus.addItem(title,value)
            self.fields['focus_mode']=focus;form.addRow('可见光对焦',focus);focus.currentIndexChanged.connect(self.changed)
            for key,title,lo,hi,initial in [('focus_distance_m','对焦距离（m）',.2,10000,100),('aperture_f','光圈 f/',1,22,2.8),('vis_blur_px','可见光光学模糊（px）',0,3,.95)]:
                self.spin(form,key,title,lo,hi,initial);self.fields[key].setDecimals(2);self.fields[key].setSingleStep(.1)
            for key,title,lo,hi,initial in [('pitch_deg','俯仰（°）',-90,20,-60),('yaw_deg','相对机头朝向（°）',-180,180,0),('fov_deg','水平视场角（°）',5,90,65),('sample_hz','采样上限（Hz）',1,30,15)]:self.spin(form,key,title,lo,hi,initial)
            for key,title,lo,hi,initial in [('ir_fov_deg','红外水平视场（°）',5,90,65),('ir_blur_px','红外光学模糊（px）',0,2,.8),('ir_noise','红外噪声',0,.1,.008),('ir_sample_hz','红外采样上限（Hz）',1,30,15)]:
                self.spin(form,key,title,lo,hi,initial);self.fields[key].setDecimals(3 if key=='ir_noise' else 2)
                self.fields[key].setSingleStep(.001 if key=='ir_noise' else .05 if key=='ir_blur_px' else 1)
            row=QHBoxLayout()
            for title,pitch in [('前视',0),('斜视',-60),('下视',-90)]:
                b=QPushButton(title);b.clicked.connect(lambda _,p=pitch:self.preset(p));row.addWidget(b)
            layout.addLayout(row)
            row=QHBoxLayout();self.aim_buttons=[]
            for title,key,step in [('抬头','pitch_deg',2),('低头','pitch_deg',-2),('左转','yaw_deg',-2),('右转','yaw_deg',2)]:
                button=QPushButton(title);button.setAutoRepeat(True);button.setAutoRepeatDelay(300);button.setAutoRepeatInterval(100)
                button.clicked.connect(lambda _,k=key,s=step:self.nudge(k,s));row.addWidget(button);self.aim_buttons.append(button)
            layout.addLayout(row)
            self.live_aim=QCheckBox('实时应用相机朝向');self.live_aim.setChecked(True);self.live_aim.toggled.connect(self.live_changed);layout.addWidget(self.live_aim)
            self.preview=QPushButton('设为主画面');self.preview.clicked.connect(lambda:show_aerial(window,self.device.currentData()));layout.addWidget(self.preview)
            note='长按方向按钮可连续调整相机。朝向独立于无人机驾驶；下视建议起飞后使用。'
        else:
            self.check(form,'vehicles_enabled','启用车辆');self.spin(form,'vehicle_density','车辆密度（%）',0,100,25)
            self.check(form,'pedestrians_enabled','启用行人');self.spin(form,'pedestrian_density','行人密度（%）',0,100,25)
            note='车辆沿地图道路行驶，行人沿人行路径自动活动。100%预算：600辆行驶车、600辆停放车、1200名行人，分布在全地图；实际可见数量取决于相机位置。'
        hint=QLabel(note);hint.setWordWrap(True);layout.addWidget(hint)
        self.status=QLabel('连接后读取实际状态');self.status.setWordWrap(True);layout.addWidget(self.status)
        if aerial:
            self.focus_info=QLabel('实际焦点：待回读');self.focus_info.setWordWrap(True);layout.addWidget(self.focus_info)
        row=QHBoxLayout();self.apply=QPushButton('应用');self.apply.clicked.connect(self.submit);row.addWidget(self.apply)
        self.save=QPushButton('保存为本场景默认');self.save.clicked.connect(self.persist);row.addWidget(self.save)
        self.reload=QPushButton('重新读取');self.reload.clicked.connect(self.load);row.addWidget(self.reload);layout.addLayout(row)
        window.client.request_completed.connect(self.completed);window.client.request_failed.connect(self.failed)
        window.client.connection_changed.connect(self.connection);window.client.state_received.connect(self.observe)
        self.loading=False;self.controls()
        if embedded:
            from PySide6.QtWidgets import QGroupBox
            self.preview.hide();hint.hide();self.live_aim.setText('方向实时生效')
            advanced=QGroupBox('相机与采样设置');advanced.setCheckable(True);advanced.setChecked(False)
            advanced_layout=QVBoxLayout(advanced);advanced_body=QWidget();advanced_form=QFormLayout(advanced_body)
            advanced_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
            for key,title in [('enabled','相机电源'),('stabilized','保持地平线'),('sample_hz','采样上限（Hz）'),('ir_enabled','红外电源'),('ir_black_hot','红外黑热'),('ir_fov_deg','红外视场'),('ir_blur_px','红外模糊'),('ir_noise','红外噪声'),('ir_sample_hz','红外采样上限')]:
                field=self.fields[key]
                label=form.labelForField(field)
                if label:label.hide()
                form.takeRow(field);advanced_form.addRow(title,field)
            advanced_layout.addWidget(advanced_body);advanced_body.hide();advanced.toggled.connect(advanced_body.setVisible)
            layout.insertWidget(layout.indexOf(self.status),advanced)
            self.save.setText('保存默认');self.reload.setText('刷新');self.apply.setText('应用参数')
            self.device.setToolTip('选择预览相机；驾驶对象需通过接管按钮明确选择')
            form.labelForField(self.device).setText('相机来源')
            for key,title in [('pitch_deg','俯仰角'),('yaw_deg','水平转向'),('fov_deg','视场角')]:
                form.labelForField(self.fields[key]).setText(title);self.fields[key].setSuffix(' °')

    def check(self,form,key,title):
        field=QCheckBox();self.fields[key]=field;form.addRow(title,field);field.toggled.connect(self.changed)

    def spin(self,form,key,title,lo,hi,value):
        field=QDoubleSpinBox();field.setRange(lo,hi);field.setDecimals(0);field.setValue(value);self.fields[key]=field
        field.setKeyboardTracking(False)
        form.addRow(title,field);field.valueChanged.connect(self.changed)

    def refresh_devices(self,state):
        if not self.aerial:return
        wanted=[(d['id'],d.get('name',d['id'])) for d in state.get('devices',[]) if d['kind']=='drone' and 'aerial' in d]
        old=self.device.currentData() or self.window.selected_drone
        if [self.device.itemData(i) for i in range(self.device.count())]==[d[0] for d in wanted]:return
        blocker=QSignalBlocker(self.device);self.device.clear()
        for ident,name in wanted:self.device.addItem(ident if name==ident else name+' · '+ident,ident)
        self.device.setCurrentIndex(max(0,self.device.findData(old)));del blocker

    def observe(self,state):
        self.refresh_devices(state)
        if self.aerial:
            data=next((d.get('aerial',{}) for d in state.get('devices',[]) if d['id']==self.device.currentData()),{})
            self.update_focus_info(data)
        if self.run and self.run!=state.get('run_id'):
            self.cancel_aim()
            self.pending=None;self.valid=False;self.dirty=False;self.status.setText('场景已切换，请重新读取');self.controls()
        if not self.aerial and self.valid and not self.dirty and self.pending is None and 'population' in state:
            data=state['population']
            self.status.setText(('正在更新生成预算' if data.get('pending') else '生成预算已应用')+'；预算不等于实际可见数量')

    def connection(self,ready,*_):
        self.cancel_aim()
        self.pending=None;self.valid=False
        if not ready:self.status.setText('已断开，画面和参数状态不可用')
        elif self.isVisible():self.load()
        self.controls()

    def update_focus_info(self,data):
        if not self.aerial:return
        if not data.get('focus_supported'):
            self.focus_info.setText('当前版本未提供对焦控制');return
        far='∞' if data.get('dof_far_infinite') else f"{data.get('dof_far_m',0):.1f} m"
        self.focus_info.setText(f"实际焦点 {data.get('actual_focus_distance_m',0):.1f} m · 估计景深 {data.get('dof_near_m',0):.1f} m 至 {far}")

    def controls(self):
        ready=self.window.client.ready and self.pending is None
        aiming=self.aerial and self.window.client.ready and self.valid and (self.pending is None or self.configuring)
        for key,field in self.fields.items():field.setEnabled((aiming if key in ('pitch_deg','yaw_deg') else ready and self.valid))
        self.apply.setEnabled(ready and self.valid);self.save.setEnabled(ready and self.valid and not self.dirty);self.reload.setEnabled(ready)
        if self.aerial:self.preview.setEnabled(ready and self.valid and bool(self.device.currentData()))
        if self.aerial:
            for key in ('focus_mode','focus_distance_m','aperture_f','vis_blur_px'):
                self.fields[key].setEnabled(ready and self.valid and self.focus_supported)
            self.fields['focus_distance_m'].setEnabled(ready and self.valid and self.focus_supported and self.fields['focus_mode'].currentData()=='manual')
            for button in self.aim_buttons:button.setEnabled(aiming)
            self.live_aim.setEnabled(aiming)

    def changed(self,*_):
        if not self.loading:
            self.dirty=True;self.status.setText('参数已修改，点击应用即可生效，无需重载场景');self.controls()
            if self.aerial and self.sender() in (self.fields['pitch_deg'],self.fields['yaw_deg']):
                self.aim_queued=True
                if self.live_aim.isChecked():self.aim_timer.start()

    def nudge(self,key,step):
        if self.valid and self.window.client.ready:
            field=self.fields[key];field.setValue(field.value()+step)

    def live_changed(self,enabled):
        if enabled and self.dirty:self.aim_queued=True;self.aim_timer.start()
        elif not enabled:self.aim_timer.stop()

    def flush_aim(self):
        if self.aerial and self.isVisible() and self.live_aim.isChecked() and self.aim_queued and self.valid and self.window.client.ready and self.pending is None:self.submit()

    def cancel_aim(self):
        self.aim_timer.stop();self.aim_queued=False;self.configuring=False

    def closeEvent(self,event):
        self.cancel_aim();super().closeEvent(event)

    def load(self,*_):
        self.cancel_aim()
        self.valid=False;self.pending=None;self.dirty=False
        if self.window.client.ready:
            payload={'device_id':self.device.currentData()} if self.aerial else {}
            if not self.aerial or payload['device_id']:
                self.pending=self.window.client.request('aerial.get_state' if self.aerial else 'population.get_state',payload)
        self.status.setText('正在读取…' if self.pending else '请先连接仿真');self.controls()

    def values(self):
        result={k:f.isChecked() if isinstance(f,QCheckBox) else f.currentData() if isinstance(f,QComboBox) else f.value() for k,f in self.fields.items()}
        if self.aerial and not self.focus_supported:
            for key in ('focus_mode','focus_distance_m','aperture_f','vis_blur_px'):result.pop(key,None)
        if self.aerial:result['device_id']=self.device.currentData()
        else:
            for key in ('vehicle_density','pedestrian_density'):result[key]/=100
        return result

    def submit(self):
        if self.pending or not self.valid:return
        self.aim_timer.stop();self.aim_queued=False;self.configuring=self.aerial
        self.pending=self.window.client.request('aerial.configure' if self.aerial else 'population.configure',self.values());self.status.setText('等待应用确认…');self.controls()

    def preset(self,pitch):
        if not self.valid or self.pending:return
        self.fields['pitch_deg'].setValue(pitch);self.fields['yaw_deg'].setValue(0);self.submit()

    def persist(self):
        if self.pending or self.dirty:return
        self.pending=self.window.client.request('observation.save',{});self.controls()

    def completed(self,request,command,submitted,state):
        if request!=self.pending:return
        queued=self.aerial and self.configuring and self.aim_queued
        draft={k:self.fields[k].value() for k in ('pitch_deg','yaw_deg')} if queued else {}
        self.configuring=False
        self.pending=None;self.run=state.get('run_id')
        data=(next((d.get('aerial') for d in state.get('devices',[]) if d['id']==self.device.currentData()),None) if self.aerial else state.get('population'))
        self.valid=isinstance(data,dict)
        self.focus_supported=bool(self.valid and data.get('focus_supported')) if self.aerial else False
        if self.aerial and self.valid:self.update_focus_info(data)
        if not self.valid:self.status.setText('当前版本或场景未提供此功能');self.controls();return
        self.loading=True
        for key,f in self.fields.items():
            value=data.get(key,False if isinstance(f,QCheckBox) else 0)
            if key.endswith('_density'):value*=100
            blocker=QSignalBlocker(f)
            if isinstance(f,QCheckBox):f.setChecked(value)
            elif isinstance(f,QComboBox):f.setCurrentIndex(max(0,f.findData(value)))
            else:f.setValue(value)
            del blocker
        self.loading=False;self.dirty=False
        if queued:
            for key,value in draft.items():
                blocker=QSignalBlocker(self.fields[key]);self.fields[key].setValue(value);del blocker
            self.dirty=True;self.aim_timer.start()
        self.status.setText('已保存本场景默认，下次启动恢复' if command=='observation.save' else '参数已确认，无需重载场景')
        if not self.aerial:
            supported=data.get('vehicles_supported') or data.get('pedestrians_supported')
            self.status.setText(('正在更新生成预算' if data.get('pending') else '生成预算已应用') if supported else '当前流送区域未发现车流／人群生成器')
            self.status.setText(self.status.text()+'；预算不等于实际可见数量')
            if command=='observation.save':self.status.setText('已保存本场景默认；预算不等于实际可见数量')
        self.controls()

    def failed(self,request,command,submitted,message):
        if request!=self.pending:return
        self.cancel_aim()
        self.pending=None;self.status.setText('未确认：'+message);self.controls()
