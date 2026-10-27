"""Device-addressed sensor drafts, correlated acknowledgements and compact forms."""
import copy
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QTabWidget, QFormLayout, QPushButton, QComboBox
from apps.desktop_app.ui.components import NumberInput, ChoiceInput, scroll

DEFINITIONS = {
    'visible': [('fov_deg','水平视场',5,120,25,'°',1,.5)],
    'infrared': [('fov_deg','水平视场',5,120,25,'°',1,.5), ('noise','传感器噪声',0,.1,.008,'',3,.001),
                 ('blur_px','光学模糊',0,2,.8,'px',2,.1), ('contrast','明暗对比',.3,3,1.35,'',2,.05),
                 ('background_detail','背景层次',0,1,.65,'',2,.05)],
    'lidar': [('horizontal_fov_deg','水平视场',.1,60,30,'°',1,.1), ('vertical_fov_deg','垂直视场',.1,60,8,'°',1,.1),
              ('range_m','量程',1,1000,300,'m',1,1), ('scan_rate_hz','扫描频率',.05,10,10,'Hz',2,.05)]}


class SensorSettings(QTabWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.device_id = window.selected_gimbal
        self.bank = {}
        self.pending = {}
        self.panels = {}
        self.generation = 0
        self.run_id = None
        for ident, title in [('visible','可见光'), ('infrared','红外'), ('lidar','激光雷达')]:
            page = QWidget(); page.setObjectName('sensorPage'); layout = QVBoxLayout(page); layout.setContentsMargins(0,10,0,0)
            source_label = QLabel(self.device_id + ' / ' + ident); source_label.setWordWrap(True); source_label.setObjectName('section'); layout.addWidget(source_label)
            label = QLabel({'visible':'1920×1080 · 原始可见光', 'infrared':'640×512 · 合成热成像，无温度标定', 'lidar':'48×12 射线 · 单帧米制点云'}[ident]); label.setWordWrap(True);label.setObjectName('muted');layout.addWidget(label)
            enabled = QCheckBox('启用采集与输出'); enabled.setChecked(True); layout.addWidget(enabled)
            hint=QLabel('启停也需应用；停用将中断此传感器的外部输出。');hint.setWordWrap(True);hint.setObjectName('hint');layout.addWidget(hint)
            fields = {'enabled':enabled}; form = QFormLayout()
            for key, text, low, high, default, unit, decimals, step in DEFINITIONS[ident]:
                widget = NumberInput(low, high, unit, decimals, step);widget.setValue(default);fields[key]=widget;form.addRow(text,widget)
            if ident == 'infrared':
                profile=ChoiceInput();profile.addItem('增强热像 · 试验版','enhanced');profile.addItem('原始热像 · 对照','legacy');fields['thermal_profile']=profile;form.addRow('成像模式',profile)
                palette=ChoiceInput();palette.addItem('白热','white_hot');palette.addItem('黑热','black_hot');fields['palette']=palette;form.addRow('显示极性',palette)
            layout.addLayout(form)
            actual=QLabel('实际生效：未连接');actual.setWordWrap(True);layout.addWidget(actual)
            status=QLabel('本次运行有效；尚未确认设备状态');status.setWordWrap(True);status.setObjectName('muted');layout.addWidget(status)
            row=QHBoxLayout();apply=QPushButton('应用更改');apply.setObjectName('primary');reset=QPushButton('撤销草稿');row.addWidget(apply);row.addWidget(reset);layout.addLayout(row)
            apply.clicked.connect(lambda _,sensor=ident:self.submit(sensor));reset.clicked.connect(lambda _,sensor=ident:self.restore(sensor))
            capture=QPushButton('保存原始单帧');capture.clicked.connect(lambda _,sensor=ident:window.capture_source(self.device_id,sensor));layout.addWidget(capture)
            layout.addStretch()
            self.panels[ident]=dict(fields=fields, actual=actual, status=status, dirty=False, confirmed=None, apply=apply, reset=reset, capture=capture, source=source_label)
            for widget in fields.values():
                signal=widget.toggled if isinstance(widget,QCheckBox) else widget.currentIndexChanged if isinstance(widget,QComboBox) else widget.valueChanged
                signal.connect(lambda _,sensor=ident:self.mark_dirty(sensor))
            # Keep acknowledgement and apply controls visible when the field area
            # needs scrolling on small windows or high-DPI displays.
            footer=QWidget();footer.setObjectName('sensorFooter');footer_layout=QVBoxLayout(footer);footer_layout.setContentsMargins(0,8,0,0)
            for widget in (actual,status):layout.removeWidget(widget);footer_layout.addWidget(widget)
            layout.removeItem(row);footer_layout.addLayout(row)
            layout.removeWidget(capture);footer_layout.addWidget(capture)
            shell=QWidget();shell.setObjectName('sensorShell');shell_layout=QVBoxLayout(shell);shell_layout.setContentsMargins(0,0,0,0)
            shell_layout.addWidget(scroll(page),1);shell_layout.addWidget(footer)
            self.addTab(shell,title)
        window.client.request_completed.connect(self.acknowledged)
        window.client.request_failed.connect(self.rejected)
        window.client.state_received.connect(self.update_state)

    def values(self, ident):
        panel=self.panels[ident]
        values={key:widget.isChecked() if isinstance(widget,QCheckBox) else widget.currentData() if isinstance(widget,QComboBox) else widget.value() for key,widget in panel['fields'].items()}
        if ident=='infrared' and panel['confirmed'] is not None and not panel['confirmed'].get('enhanced_available',False):
            for key in ('thermal_profile','blur_px','contrast','background_detail'):values.pop(key,None)
        return values

    def fill(self, ident, data):
        if ident=='infrared' and ('thermal_profile' not in data or not data.get('enhanced_available',True)):data=dict(data,thermal_profile='legacy')
        for key,widget in self.panels[ident]['fields'].items():
            if key not in data:continue
            blocker=QSignalBlocker(widget)
            if isinstance(widget,QCheckBox):widget.setChecked(data[key])
            elif isinstance(widget,QComboBox):widget.setCurrentIndex(widget.findData(data[key]))
            else:widget.setValue(data[key])
            del blocker

    def stash(self):
        for ident,panel in self.panels.items():
            self.bank[(self.device_id,ident)] = dict(values=self.values(ident), confirmed=copy.deepcopy(panel['confirmed']), dirty=panel['dirty'], status=panel['status'].text())

    def select_device(self, device):
        self.stash()
        self.device_id=device
        for ident,panel in self.panels.items():
            saved=self.bank.get((device,ident),{})
            panel['confirmed']=copy.deepcopy(saved.get('confirmed'));panel['dirty']=saved.get('dirty',False)
            # Unknown devices start with defaults rather than the previously inspected values.
            defaults={key:default for key,_,_,_,default,_,_,_ in DEFINITIONS[ident]}
            defaults['enabled']=True
            if ident=='infrared':defaults.update(palette='white_hot',thermal_profile='enhanced')
            self.fill(ident,saved.get('values',defaults));panel['source'].setText(device+' / '+ident)
            panel['status'].setText(saved.get('status','等待实际参数确认；本次运行有效'))
        self.render()
        if self.window.client.ready:self.window.client.request('sim.get_state',{'device_id':device})

    def mark_dirty(self, ident):
        panel=self.panels[ident]
        actual=panel['confirmed']
        panel['dirty']=actual is None or any(self.values(ident).get(k)!=v for k,v in actual.items() if k in panel['fields'])
        panel['status'].setText('有未应用的更改 · 本次运行有效' if panel['dirty'] else '与实际参数一致')
        self.stash();self.render()

    def restore(self, ident):
        panel=self.panels[ident]
        if panel['confirmed'] is not None:
            self.fill(ident,panel['confirmed']);panel['dirty']=False;panel['status'].setText('草稿已恢复为实际生效值');self.stash();self.render()

    def submit(self, ident):
        key=(self.device_id,ident)
        if any(item['key']==key for item in self.pending.values()):return
        panel=self.panels[ident]
        if not self.window.client.ready or panel['confirmed'] is None:
            panel['status'].setText('请先连接并等待此设备的实际参数');return
        for field in panel['fields'].values():
            if isinstance(field,NumberInput):
                field.interpretText()
                if not field.hasAcceptableInput():panel['status'].setText('请检查数值与允许范围');return
        draft=self.values(ident)
        request=self.window.client.request('sensor.configure',dict(device_id=self.device_id,sensor=ident,**draft))
        if request:
            self.pending[request]=dict(key=key, snapshot=copy.deepcopy(draft), generation=self.generation)
            panel['status'].setText('等待 UE 确认…');self.stash();self.render()
        else:panel['status'].setText('提交失败，请检查连接或稍后重试')

    def update_state(self, state):
        run_id=state.get('run_id')
        if run_id and self.run_id and run_id!=self.run_id:self.disconnected()
        if run_id:self.run_id=run_id
        device=state.get('gimbal_id','ptz-01')
        devices=state.get('devices',[])
        if devices and self.device_id not in {d['id'] for d in devices if d['kind']=='gimbal'}:
            for panel in self.panels.values():
                panel['confirmed']=None;panel['status'].setText('来源不存在；草稿保留，请选择其他设备')
        for ident,data in state.get('sensors',{}).items():
            if ident not in self.panels:continue
            saved=self.bank.setdefault((device,ident),dict(values=dict(data),dirty=False,status='已确认 · 本次运行有效'))
            saved['confirmed']=dict(data)
            if device!=self.device_id:
                if not saved.get('dirty'):saved['values']=dict(data)
                continue
            panel=self.panels[ident];panel['confirmed']=dict(data)
            if not panel['dirty'] and not any(item['key']==(device,ident) for item in self.pending.values()):self.fill(ident,data)
        self.stash();self.render()

    def acknowledged(self, request, command, payload, state):
        item=self.pending.pop(request,None)
        if command!='sensor.configure' or item is None:return
        device,sensor=item['key']
        if item['generation']!=self.generation or state.get('gimbal_id')!=device:return
        actual=state.get('sensors',{}).get(sensor)
        if actual is None:return
        self.stash()
        saved=self.bank[(device,sensor)]
        saved['confirmed']=dict(actual)
        saved['dirty']=any(saved['values'].get(k)!=v for k,v in item['snapshot'].items())
        if not saved['dirty']:saved['values']=dict(actual)
        saved['status']='已生效；另有未应用修改' if saved['dirty'] else '已生效 · 本次运行有效'
        if self.device_id==device:
            panel=self.panels[sensor];panel['confirmed']=dict(actual);panel['dirty']=saved['dirty'];self.fill(sensor,saved['values']);panel['status'].setText(saved['status'])
        self.render()

    def rejected(self, request, command, payload, message):
        item=self.pending.pop(request,None)
        if item is None:return
        self.stash();saved=self.bank.get(item['key'])
        text=('结果待确认：' if '未确认' in message or '超时' in message else '应用失败：')+message
        if saved:saved['dirty']=True;saved['status']=text
        if item['key'][0]==self.device_id:
            panel=self.panels[item['key'][1]];panel['dirty']=True;panel['status'].setText(text)
        self.render()

    def render(self):
        for ident,panel in self.panels.items():
            actual=panel['confirmed'];waiting=any(item['key']==(self.device_id,ident) for item in self.pending.values())
            panel['apply'].setEnabled(self.window.client.ready and actual is not None and panel['dirty'] and not waiting)
            panel['reset'].setEnabled(actual is not None and panel['dirty'])
            panel['capture'].setEnabled(self.window.client.ready and actual is not None and bool(actual.get('enabled')))
            if actual is None:panel['actual'].setText('实际生效：尚未确认')
            else:
                info='采集中' if actual.get('enabled') else '已停用'
                if 'fov_deg' in actual:info+=f" · FOV {actual['fov_deg']:.1f}°"
                else:info+=f" · {actual.get('range_m',0):g} m · {actual.get('scan_rate_hz',0):g} Hz"
                if ident=='infrared':info+=' · '+('增强热像' if actual.get('thermal_profile')=='enhanced' else '原始热像')
                panel['actual'].setText('实际生效：'+info)
            index=('visible','infrared','lidar').index(ident)
            title=('可见光','红外','激光雷达')[index]
            self.setTabText(index,title+(' •' if panel['dirty'] else ''))
            status=panel['status'].text()
            color='#ff9292' if any(word in status for word in ('失败','超时','待确认：')) else '#f3c66a' if panel['dirty'] else '#b4bcc8'
            panel['status'].setStyleSheet('color:'+color+';')
            for key,widget in panel['fields'].items():
                if ident=='infrared' and key in ('thermal_profile','blur_px','contrast','background_detail'):
                    available=actual is not None and actual.get('enhanced_available',False)
                    widget.setEnabled(available)
                    widget.setToolTip('需要包含试验红外材质的新版 UE' if not available else '合成成像参数；尚未做真实相机标定')
                changed=panel['dirty'] and (actual is None or self.values(ident).get(key)!=actual.get(key))
                if widget.property('dirty')!=changed:
                    widget.setProperty('dirty',changed);widget.style().unpolish(widget);widget.style().polish(widget)

    def disconnected(self):
        self.stash();self.generation+=1;self.pending.clear()
        for saved in self.bank.values():saved['confirmed']=None
        for panel in self.panels.values():
            panel['confirmed']=None;panel['status'].setText('连接已断开；草稿保留，重连后确认实际值')
        self.render()
