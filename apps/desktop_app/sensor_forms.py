"""Device-addressed sensor drafts, correlated acknowledgements and compact forms."""
import copy
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QTabWidget, QFormLayout, QPushButton, QComboBox
from apps.desktop_app.ui.components import NumberInput, ChoiceInput, scroll
from core.infrared_presets import DETECTOR_FIELDS

EXTRINSIC_FIELDS=('mount_x_cm','mount_y_cm','mount_z_cm','boresight_pitch_deg','boresight_yaw_deg','boresight_roll_deg')

DEFINITIONS = {
    'event':[('fov_deg','水平视场',5,120,25,'°',1,.5),('sample_hz','渲染采样上限',1,120,30,'Hz',0,1),('positive_threshold','正事件阈值',.01,1,.2,'ln',3,.01),('negative_threshold','负事件阈值',.01,1,.2,'ln',3,.01),('refractory_us','像素不应期',0,100000,100,'µs',0,10)],
    'visible': [('fov_deg','水平视场',5,120,25,'°',1,.5)],
    'infrared': [('fov_deg','水平视场',5,120,25,'°',1,.5), ('noise','传感器噪声',0,.1,.008,'',3,.001),
                 ('blur_px','光学模糊',0,2,.8,'px',2,.1), ('contrast','明暗对比',.3,3,1.35,'',2,.05),
                 ('background_detail','背景层次',0,1,.65,'',2,.05),
                 ('agc_response_s','增益适应时间',.1,10,1,'s',2,.1),
                 ('manual_low','手动信号下限',0,1,0,'',3,.01),('manual_high','手动信号上限',0,1,1,'',3,.01),
                 ('brightness','显示亮度',-.3,.3,0,'',2,.01),('sky_denoise','云层去颗粒',0,1,0,'',2,.1),
                 ('noise_seed','噪声种子',0,2147483647,1337,'',0,1)],
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
        self.power_supported=False
        for ident, title in [('visible','可见光'), ('infrared','红外'), ('lidar','激光雷达'),('event','事件相机')]:
            page = QWidget(); page.setObjectName('sensorPage'); layout = QVBoxLayout(page); layout.setContentsMargins(0,10,0,0)
            source_label = QLabel(self.device_id + ' / ' + ident); source_label.setWordWrap(True); source_label.setObjectName('section'); layout.addWidget(source_label)
            label = QLabel({'visible':'1920×1080 · 原始可见光', 'infrared':'640×512 · 合成热成像，无温度标定', 'lidar':'48×12 射线 · 单帧米制点云', 'event':'640×480 · 独立光心、帧驱动事件近似；时间戳插值，不代表硬件微秒精度'}[ident]); label.setWordWrap(True);label.setObjectName('muted');layout.addWidget(label)
            enabled = QCheckBox('启用采集与输出'); enabled.setChecked(ident!='event'); layout.addWidget(enabled)
            hint=QLabel('启停也需应用；停用将中断此传感器的外部输出。');hint.setWordWrap(True);hint.setObjectName('hint');layout.addWidget(hint)
            fields = {'enabled':enabled}; form = QFormLayout()
            for key, text, low, high, default, unit, decimals, step in DEFINITIONS[ident]:
                widget = NumberInput(low, high, unit, decimals, step);widget.setValue(default);fields[key]=widget;form.addRow(text,widget)
            if ident in ('visible','infrared','event'):
                definitions=[('mount_x_cm','镜头前向偏置',100,0,'cm'),('mount_y_cm','镜头右向偏置',100,0 if ident=='event' else 6 if ident=='infrared' else -6,'cm'),('mount_z_cm','镜头上向偏置',100,2 if ident=='event' else 0,'cm'),
                    ('boresight_pitch_deg','视轴俯仰偏差',15,.1 if ident=='infrared' else 0,'°'),('boresight_yaw_deg','视轴偏航偏差',15,.2 if ident=='infrared' else 0,'°'),('boresight_roll_deg','视轴滚转偏差',15,0,'°')]
                for key,title,limit,default,unit in definitions:
                    widget=NumberInput(-limit,limit,unit,2,.1);widget.setValue(default);fields[key]=widget;form.addRow(title,widget)
            if ident == 'infrared':
                profile=ChoiceInput();profile.addItem('红外','facade');profile.hide();fields['thermal_profile']=profile
                palette=ChoiceInput();palette.addItem('白热','white_hot');palette.addItem('黑热','black_hot');fields['palette']=palette;form.addRow('显示极性',palette)
                agc=QCheckBox('自动调整灰度范围');agc.setChecked(True);fields['agc_enabled']=agc;form.addRow('自动增益',agc)
                gain=ChoiceInput()
                for title,value in [('自动','auto'),('锁定当前范围','locked'),('手动信号范围','manual')]:gain.addItem(title,value)
                fields['gain_mode']=gain;form.addRow('增益模式',gain)
                stable=QCheckBox('稳定背景亮度');stable.setToolTip('转动云台或天空占比变化时减小背景明暗波动；没有足够背景时保持当前范围。')
                fields['stable_agc']=stable;form.addRow('稳定自动增益',stable)
                sampling=ChoiceInput();sampling.addItem('1× · 标准开销',1);sampling.addItem('2× · 细采样试验，开销较大',2);fields['sampling_scale']=sampling;form.addRow('红外采样',sampling)
            # Move advanced rows without replacing controls or their identity.
            groups=[]
            if ident=='infrared':groups.append(('增益与探测器高级参数', ['noise','blur_px','background_detail','agc_response_s','manual_low','manual_high','sky_denoise','noise_seed','agc_enabled','stable_agc','sampling_scale']))
            if ident in ('visible','infrared','event'):groups.append(('安装与相机几何',list(EXTRINSIC_FIELDS)))
            folded=[]
            for title,keys in groups:
                content=QWidget();advanced=QFormLayout(content);advanced.setContentsMargins(4,6,4,6)
                for key in keys:
                    if key not in fields:continue
                    taken=form.takeRow(fields[key])
                    if taken.labelItem is not None:advanced.addRow(taken.labelItem.widget(),fields[key])
                    else:advanced.addRow(fields[key])
                content.hide();toggle=QPushButton('展开 · '+title);toggle.setObjectName('ghost');toggle.setCheckable(True)
                toggle.toggled.connect(content.setVisible)
                toggle.toggled.connect(lambda checked,b=toggle,t=title:b.setText(('收起 · ' if checked else '展开 · ')+t))
                folded.append((toggle,content))
            layout.addLayout(form)
            for toggle,content in folded:layout.addWidget(toggle);layout.addWidget(content)
            actual=QLabel('实际生效：未连接');actual.setWordWrap(True);layout.addWidget(actual)
            status=QLabel('本次运行有效；尚未确认设备状态');status.setWordWrap(True);status.setObjectName('muted');layout.addWidget(status)
            row=QHBoxLayout();apply=QPushButton('应用更改');apply.setObjectName('primary');reset=QPushButton('撤销草稿');row.addWidget(apply);row.addWidget(reset);layout.addLayout(row)
            apply.clicked.connect(lambda _,sensor=ident:self.submit(sensor));reset.clicked.connect(lambda _,sensor=ident:self.restore(sensor))
            capture=QPushButton('保存最近事件窗口' if ident=='event' else '保存原始单帧');capture.clicked.connect(lambda _,sensor=ident:window.capture_source(self.device_id,sensor));layout.addWidget(capture)
            layout.addStretch()
            self.panels[ident]=dict(fields=fields, actual=actual, status=status, dirty=False, confirmed=None, apply=apply, reset=reset, capture=capture, source=source_label, power_hint=hint)
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
            self.addTab(shell,{'visible':'可见光','infrared':'红外','lidar':'激光雷达','event':'事件相机'}[ident])
        window.client.request_completed.connect(self.acknowledged)
        window.client.request_failed.connect(self.rejected)
        window.client.state_received.connect(self.update_state)

    def values(self, ident):
        panel=self.panels[ident]
        values={key:widget.isChecked() if isinstance(widget,QCheckBox) else widget.currentData() if isinstance(widget,QComboBox) else widget.value() for key,widget in panel['fields'].items()}
        if not (panel['confirmed'] or {}).get('extrinsics_supported'):
            for key in EXTRINSIC_FIELDS:values.pop(key,None)
        if ident=='infrared' and panel['confirmed'] is not None and not panel['confirmed'].get('enhanced_available',False):
            for key in ('thermal_profile','blur_px','contrast','background_detail'):values.pop(key,None)
        if ident=='infrared' and not (panel['confirmed'] or {}).get('facade_available'):
            values.pop('thermal_profile',None)
        if ident=='infrared' and (panel['confirmed'] is None or not panel['confirmed'].get('reference_available',False)):
            for key in ('agc_enabled','agc_response_s','sampling_scale'):values.pop(key,None)
        if ident=='infrared':
            if not (panel['confirmed'] or {}).get('detector_controls_available'):
                for key in DETECTOR_FIELDS:values.pop(key,None)
            else:values['agc_enabled']=values['gain_mode']=='auto'
        return values

    def fill(self, ident, data):
        if ident=='infrared':data=dict(data,thermal_profile='facade')
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
            defaults['enabled']=ident!='event'
            if ident=='event':defaults.update(mount_x_cm=0,mount_y_cm=0,mount_z_cm=2,boresight_pitch_deg=0,boresight_yaw_deg=0,boresight_roll_deg=0)
            if ident=='infrared':defaults.update(palette='white_hot',thermal_profile='facade',agc_enabled=True,sampling_scale=1,gain_mode='auto',stable_agc=True)
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
        if ident=='infrared' and 'manual_low' in draft and draft['manual_high']-draft['manual_low']<.01-1e-9:
            panel['status'].setText('手动上限须比下限至少大 0.01（归一化信号）');return
        request=self.window.client.request('sensor.configure',dict(device_id=self.device_id,sensor=ident,**draft))
        if request:
            self.pending[request]=dict(key=key, snapshot=copy.deepcopy(draft), generation=self.generation)
            panel['status'].setText('等待 UE 确认…');self.stash();self.render()
        else:panel['status'].setText('提交失败，请检查连接或稍后重试')

    def update_state(self, state):
        self.power_supported=bool(state.get('sensor_power_supported'))
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
            if not panel['dirty'] and not any(item['key']==(device,ident) for item in self.pending.values()):
                self.fill(ident,data)
                if '尚未确认设备状态' in panel['status'].text() or panel['status'].text().startswith('连接已断开'):
                    panel['status'].setText('已确认 · 本次运行有效')
        self.stash();self.render()

    def acknowledged(self, request, command, payload, state):
        item=self.pending.pop(request,None)
        if command not in ('sensor.configure','sensor.set_enabled') or item is None:return
        device,sensor=item['key']
        if item['generation']!=self.generation or state.get('gimbal_id')!=device:return
        actual=state.get('sensors',{}).get(sensor)
        if actual is None:return
        self.stash()
        saved=self.bank[(device,sensor)]
        saved['confirmed']=dict(actual)
        if item.get('action')=='power':
            saved['values']['enabled']=actual['enabled']
            saved['dirty']=any(v!=actual.get(k) for k,v in saved['values'].items() if k in actual)
        else:saved['dirty']=any(saved['values'].get(k)!=v for k,v in item['snapshot'].items())
        if not saved['dirty']:saved['values']=dict(actual)
        saved['status']='已生效；另有未应用修改' if saved['dirty'] else '已生效 · 本次运行有效'
        if self.device_id==device:
            panel=self.panels[sensor];panel['confirmed']=dict(actual);panel['dirty']=saved['dirty'];self.fill(sensor,saved['values']);panel['status'].setText(saved['status'])
        self.render()

    def submit_power(self, ident):
        key=(self.device_id,ident);panel=self.panels[ident]
        if not self.power_supported or not self.window.client.ready or panel['confirmed'] is None:return
        if any(item['key']==key for item in self.pending.values()):return
        payload=dict(device_id=self.device_id,sensor=ident,enabled=not panel['confirmed']['enabled'])
        request=self.window.client.request('sensor.set_enabled',payload)
        if request:
            self.pending[request]=dict(key=key,snapshot=dict(enabled=payload['enabled']),generation=self.generation,action='power')
            panel['status'].setText('等待启停确认…');self.stash();self.render()

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
        if hasattr(self,'power_panel'):self.power_panel.refresh()
        for ident,panel in self.panels.items():
            actual=panel['confirmed'];waiting=any(item['key']==(self.device_id,ident) for item in self.pending.values())
            panel['fields']['enabled'].setVisible(not self.power_supported)
            panel['power_hint'].setVisible(not self.power_supported)
            panel['apply'].setEnabled(self.window.client.ready and actual is not None and panel['dirty'] and not waiting)
            panel['reset'].setEnabled(actual is not None and panel['dirty'])
            panel['capture'].setEnabled(self.window.client.ready and actual is not None and bool(actual.get('enabled')))
            if actual is None:panel['actual'].setText('实际生效：尚未确认')
            else:
                info='采集中' if actual.get('enabled') else '已停用'
                if 'fov_deg' in actual:info+=f" · FOV {actual['fov_deg']:.1f}°"
                else:info+=f" · {actual.get('range_m',0):g} m · {actual.get('scan_rate_hz',0):g} Hz"
                if ident=='infrared':
                    info+=' · '+{'facade':'红外','classified':'材料热像','reference':'实拍参考','enhanced':'增强热像','legacy':'原始热像'}.get(actual.get('thermal_profile'),'原始热像')
                    counts=actual.get('class_pixels',[])
                    if actual.get('thermal_profile') in ('classified','facade') and len(counts)==7 and sum(counts)>0:
                        info+=f' · 材料覆盖 {100*sum(counts[1:])/sum(counts):.0f}%'
                if ident=='event':info+=f" · {actual.get('actual_sample_hz',0):.1f} Hz · {actual.get('events_total',0)} 事件"
                panel['actual'].setText('实际生效：'+info)
                panel['actual'].setToolTip('材料覆盖表示当前视角中被材料规则覆盖的像素占比；其余使用默认背景，不代表分类准确率。' if ident=='infrared' and actual.get('thermal_profile') in ('classified','facade') else '')
            index=('visible','infrared','lidar','event').index(ident)
            title=('可见光','红外','激光雷达','事件相机')[index]
            self.setTabText(index,title+(' •' if panel['dirty'] else ''))
            status=panel['status'].text()
            color='#ff9292' if any(word in status for word in ('失败','超时','待确认：')) else '#f3c66a' if panel['dirty'] else '#b4bcc8'
            panel['status'].setStyleSheet('color:'+color+';')
            for key,widget in panel['fields'].items():
                if key in EXTRINSIC_FIELDS:
                    widget.setEnabled(bool(actual and actual.get('extrinsics_supported')))
                    widget.setToolTip('相对云台镜头头部的安装位置（X前/Y右/Z上，厘米）和视轴偏差；两相机独立成像，参数仅本次运行有效。')
                if ident=='infrared' and key in DETECTOR_FIELDS:
                    available=bool(actual and actual.get('detector_controls_available'))
                    readout=panel['fields']['thermal_profile'].currentData() in ('reference','classified','facade')
                    mode=panel['fields']['gain_mode'].currentData()
                    widget.setEnabled(available and readout and (key not in ('manual_low','manual_high') or mode=='manual') and (key!='stable_agc' or mode=='auto') and (key!='sky_denoise' or panel['fields']['thermal_profile'].currentData()=='facade'))
                    widget.setToolTip('归一化工程信号；不是摄氏温度。锁定使用实际生效的增益范围，手动使用上下限；云层滤波不混合目标像素。')
                if ident=='infrared' and key in ('agc_enabled','agc_response_s','sampling_scale'):
                    widget.setEnabled(bool(actual and actual.get('reference_available') and panel['fields']['thermal_profile'].currentData() in ('reference','classified','facade')))
                    widget.setToolTip('当前红外成像；2×采样增加GPU和读回开销；不是相机物理标定')
                if ident=='infrared' and key in ('thermal_profile','blur_px','contrast','background_detail'):
                    available=actual is not None and actual.get('enhanced_available',False)
                    widget.setEnabled(available)
                    widget.setToolTip('需要包含试验红外材质的新版 UE' if not available else '合成成像参数；尚未做真实相机标定')
                    if key=='thermal_profile':
                        facade_item=widget.model().item(widget.findData('facade'))
                        if facade_item is not None:facade_item.setEnabled(bool(actual and actual.get('facade_available')))
                        classified_item=widget.model().item(widget.findData('classified'))
                        if classified_item is not None:classified_item.setEnabled(bool(actual and actual.get('classified_available')))
                        item=widget.model().item(widget.findData('reference'))
                        if item is not None:item.setEnabled(bool(actual and actual.get('reference_available')))
                changed=panel['dirty'] and (actual is None or self.values(ident).get(key)!=actual.get(key))
                if widget.property('dirty')!=changed:
                    widget.setProperty('dirty',changed);widget.style().unpolish(widget);widget.style().polish(widget)
            if ident=='infrared':
                available=bool(actual and actual.get('detector_controls_available'))
                if available:
                    blocker=QSignalBlocker(panel['fields']['agc_enabled']);panel['fields']['agc_enabled'].setChecked(panel['fields']['gain_mode'].currentData()=='auto');del blocker
                    panel['fields']['agc_enabled'].setEnabled(False)
                    panel['actual'].setText(panel['actual'].text()+f" · 灰度范围 {actual.get('agc_low',0):.3f}–{actual.get('agc_high',1):.3f}")

    def disconnected(self):
        self.stash();self.generation+=1;self.pending.clear()
        for saved in self.bank.values():saved['confirmed']=None
        for panel in self.panels.values():
            panel['confirmed']=None;panel['status'].setText('连接已断开；草稿保留，重连后确认实际值')
        self.render()
