"""Task-oriented workbench using the existing addressed camera and flight owners."""
from PySide6.QtCore import Qt,QSignalBlocker,QTimer,QEvent
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QPushButton,QComboBox,QButtonGroup,QLabel
from apps.desktop_app.ui.components import scroll
from apps.desktop_app.observation_panel import ObservationDialog,save_aerial_frame
from apps.desktop_app.source_registry import Source


class MissionWorkspace:
    def __init__(self,w):
        self.w=w;self.mode='observation';self.previous=None;self.displayed_camera=None;self.tree_visible=True
        self.panel=ObservationDialog(w,True,embedded=True);w.aerial_dialog=self.panel
        self.aim_keys=set();self.key_timer=QTimer(w);self.key_timer.setInterval(100);self.key_timer.timeout.connect(self.key_step)
        w.inspectors.addTab(scroll(self.panel),'航拍相机')
        self.panel.device.currentIndexChanged.connect(self.camera_changed)
        self.panel.device.setAccessibleName('航拍相机来源')
        # One explicit workspace choice above the viewport, independent of piloting.
        self.bar=QWidget();self.bar.setObjectName('panel');row=QHBoxLayout(self.bar);row.setContentsMargins(10,6,10,6)
        self.layout_reset=next((b for b in w.gallery.findChildren(QPushButton) if '恢复布局' in b.text()),None)
        self.group=QButtonGroup(w)
        for mode,title in [('observation','云台观测'),('aerial','无人机航拍')]:
            button=QPushButton(title);button.setCheckable(True);self.group.addButton(button);row.addWidget(button)
            button.clicked.connect(lambda _,m=mode:self.choose(m));button.setChecked(mode==self.mode)
            setattr(self,mode+'_button',button)
        self.modality=QComboBox();self.modality.addItem('可见光','aerial');self.modality.addItem('红外','aerial_infrared');self.modality.addItem('双光并排','both');self.modality.currentIndexChanged.connect(lambda _:self.camera_changed(force=True));row.addWidget(self.modality);self.modality.hide()
        row.addStretch();self.caption=QLabel('选择工作方式');row.addWidget(self.caption)
        self.reference=QPushButton('场景参考');self.reference.setCheckable(True);self.reference.toggled.connect(lambda _:self.camera_changed(force=True));row.addWidget(self.reference);self.reference.hide()
        self.capture=QPushButton('保存航拍帧');self.capture.clicked.connect(lambda:save_aerial_frame(w,self.panel.device.currentData()));row.addWidget(self.capture);self.capture.hide()
        w.gallery.layout().insertWidget(0,self.bar)
        # The original scene menu becomes the sole home for scene-wide controls.
        w.scene_tools_menu.removeAction(w.aerial_action)
        w.scene_tools.setText('场景设置');w.scene_tools.setToolTip('天气、人车密度、性能画质')
        w.scene_tools_menu.addSeparator();w.scene_tools_menu.addAction('运行诊断…',w.machine_summary.open)
        w.scene_tools_menu.addAction(w.fullscreen_action)
        # Replace the seldom-used context button with a directly accessible camera.
        side=w.inspectors.parentWidget();side_layout=side.layout()
        context_row=next(side_layout.itemAt(i).layout() for i in range(side_layout.count()) if side_layout.itemAt(i).layout() and any(side_layout.itemAt(i).layout().itemAt(j).widget()==w.context_group.button(0) for j in range(side_layout.itemAt(i).layout().count())))
        self.sensor_editor_button=next((context_row.itemAt(i).widget() for i in range(context_row.count()) if isinstance(context_row.itemAt(i).widget(),QPushButton) and context_row.itemAt(i).widget().text()=='参数'),None)
        w.context_group.button(0).setText('驾驶')
        aerial=QPushButton('相机');aerial.setCheckable(True);w.context_group.addButton(aerial,3);context_row.insertWidget(1,aerial)
        aerial.clicked.connect(lambda:self.open_aerial())
        # Flight safety and explicit takeover stay next to the camera controls.
        w.manual_takeover.setText('接管此无人机驾驶')
        self.take_camera=QPushButton('驾驶这架无人机');self.take_camera.clicked.connect(self.takeover)
        w.drone_safety.layout().addWidget(self.take_camera);w.drone_safety.layout().addWidget(w.manual_takeover)
        self.take_camera.hide()
        # Hardware detail belongs in diagnostics, retaining only useful live status.
        w.machine_summary.gpu.hide();w.machine_summary.vram.hide()
        for label in w.machine_summary.findChildren(QLabel):
            if label.text()=='仿真运行主机':label.setText('运行状态')
        w.inspectors.currentChanged.connect(self.context_changed)
        w.client.state_received.connect(self.observe)
        w.client.connection_changed.connect(self.connection)
        self.context_changed(w.inspectors.currentIndex())
        w.context_group.button(3).hide()

    def open_aerial(self,device=None):
        if device:
            index=self.panel.device.findData(device)
            if index>=0:self.panel.device.setCurrentIndex(index)
        self.choose('aerial');self.w.pages.setCurrentIndex(1)
        self.w.inspectors.parentWidget().show()
        self.w.inspectors.setCurrentIndex(3)
        if self.panel.pending is None:self.panel.load()

    def choose(self,mode):
        w=self.w;gallery=w.gallery
        if mode=='aerial':
            if self.mode!='aerial':
                self.previous=(list(gallery.sources),gallery.mode,gallery.expanded)
                self.tree_visible=not w.tree_panel.isHidden();w.tree_panel.hide()
            self.mode=mode;w.inspectors.setCurrentIndex(3);self.camera_changed()
            if not self.panel.valid and self.panel.pending is None:self.panel.load()
        else:
            self.panel.cancel_aim()
            self.stop_keys()
            if self.mode=='aerial' and self.previous:
                gallery.sources,gallery.mode,gallery.expanded=self.previous;self.previous=None
                blocker=QSignalBlocker(gallery.layout_choice);gallery.layout_choice.setCurrentIndex(gallery.layout_choice.findData(gallery.mode));del blocker;gallery.arrange()
            self.mode=mode;self.displayed_camera=None;w.inspectors.setCurrentIndex(1)
            w.tree_panel.setVisible(self.tree_visible)
        self.aerial_button.setChecked(mode=='aerial');self.observation_button.setChecked(mode=='observation')
        self.capture.setVisible(mode=='aerial');self.capture.setEnabled(w.client.ready and bool(self.panel.device.currentData()))
        self.reference.setVisible(mode=='aerial');self.modality.setVisible(mode=='aerial')
        w.context_group.button(3).setVisible(mode=='aerial')
        w.context_group.button(1).setVisible(mode!='aerial')
        if self.sensor_editor_button:self.sensor_editor_button.setVisible(mode!='aerial')
        w.fleet_selection.gimbal.setVisible(mode!='aerial');w.fleet_selection.layout().labelForField(w.fleet_selection.gimbal).setVisible(mode!='aerial')
        w.observer_mode.setVisible(mode!='aerial');gallery.layout_choice.setVisible(mode!='aerial');gallery.add_button.setVisible(mode!='aerial')
        if self.layout_reset:self.layout_reset.setVisible(mode!='aerial')
        for card in gallery.cards.values():
            for button in card.findChildren(QPushButton):
                if button.text()=='航拍':button.setVisible(mode!='aerial')
        gallery.note.setText('主画面为机载相机 · 右侧调整朝向 · 滚轮缩放 · 双击复位' if mode=='aerial' else '双击设备数据源加入画面 · 右侧控制 · 滚轮缩放')
        self.context_changed(w.inspectors.currentIndex())

    def camera_changed(self,*_,force=False):
        w=self.w;device=self.panel.device.currentData()
        if self.mode!='aerial' or not device:return
        chosen=self.modality.currentData()
        self.capture.setText('保存红外帧' if chosen=='aerial_infrared' else '保存可见光帧')
        selected=['aerial','aerial_infrared'] if chosen=='both' else [chosen]
        if not force and self.displayed_camera==device and all(device+'/'+v in w.gallery.sources for v in selected):return
        for v in selected:
            source=Source(device,v);w.gallery.registry[source.key]=source
        w.gallery.sources=[device+'/'+v for v in selected]+(['scene/observer'] if self.reference.isChecked() else []);w.gallery.mode='custom';w.gallery.expanded=None
        blocker=QSignalBlocker(w.gallery.layout_choice);w.gallery.layout_choice.setCurrentIndex(3);del blocker
        w.gallery.arrange();self.displayed_camera=device
        self.caption.setText('航拍来源 · '+device);self.context_changed(w.inspectors.currentIndex())

    def takeover(self):
        device=self.panel.device.currentData()
        if device and self.w.client.ready:self.w.fleet_selection.select('drone',device)

    def context_changed(self,index):
        camera=self.panel.device.currentData();different=camera and camera!=self.w.selected_drone
        self.w.manual_takeover.setText('键盘驾驶 · '+self.w.selected_drone)
        self.take_camera.setText('切换驾驶到 '+(camera or '—'))
        self.take_camera.setVisible(index==3 and bool(different));self.take_camera.setEnabled(self.w.client.ready)
        if index==3:
            self.w.inspector_title.setText('航拍相机 · '+(camera or '—'));self.w.inspector_takeover.hide()
        elif self.mode=='observation':self.caption.setText('云台观测 · '+self.w.selected_gimbal)

    def observe(self,state):
        if self.mode=='aerial':
            self.camera_changed()
            if self.panel.isVisible() and not self.panel.valid and self.panel.pending is None:self.panel.load()
        self.context_changed(self.w.inspectors.currentIndex())
        key=(self.panel.device.currentData() or '')+'/'+('aerial_infrared' if self.modality.currentData()=='aerial_infrared' else 'aerial')
        self.capture.setEnabled(self.w.client.ready and key in self.w.gallery.frames and key not in self.w.gallery.messages)

    def connection(self,ready,*_):
        self.capture.setEnabled(ready and bool(self.panel.device.currentData()))
        if not ready:self.panel.cancel_aim();self.stop_keys()

    def stop_keys(self):
        self.aim_keys.clear();self.key_timer.stop()

    def key_step(self):
        if self.mode!='aerial' or not self.w.client.ready or not self.panel.valid:
            self.stop_keys();return
        pitch=2*((Qt.Key.Key_Up in self.aim_keys)-(Qt.Key.Key_Down in self.aim_keys))
        yaw=2*((Qt.Key.Key_Right in self.aim_keys)-(Qt.Key.Key_Left in self.aim_keys))
        if pitch:self.panel.nudge('pitch_deg',pitch)
        if yaw:self.panel.nudge('yaw_deg',yaw)

    def handle_key(self,event):
        if self.mode!='aerial':return False
        if event.type()==QEvent.Type.ShortcutOverride:event.accept();return True
        if not event.isAutoRepeat():
            if event.type()==QEvent.Type.KeyPress:
                self.aim_keys.add(event.key());self.key_step()
                if self.aim_keys:self.key_timer.start()
            else:
                self.aim_keys.discard(event.key())
                if not self.aim_keys:self.key_timer.stop()
        event.accept();return True
