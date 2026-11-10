"""Compact live machine status and a correlated environment control dialog."""
from PySide6.QtCore import QTime, QSignalBlocker,QTimer,Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDialog,
    QFormLayout,QCheckBox,QTimeEdit,QSpinBox)
from core.runtime_metrics import PerformanceAdvice,PerformanceRating,number


def gib(value):return '未提供' if value is None else f'{value/1024**3:.2f} GiB'
def percent(value):return '未提供' if value is None else f'{value:.0f}%'


class RuntimePanel(QWidget):
    rating_changed=Signal(str,str,str)
    def __init__(self,window):
        super().__init__();self.window=window;self.advice=PerformanceAdvice();self.rating_model=PerformanceRating();self.dialog=None
        row=QHBoxLayout(self);row.setContentsMargins(10,4,10,4)
        column=QVBoxLayout();column.setSpacing(2)
        self.rating=QLabel('运行评估 · 未评估');column.addWidget(self.rating)
        self.hardware=QLabel();self.hardware.setWordWrap(True);column.addWidget(self.hardware)
        self.details=QLabel();self.details.setObjectName('muted');self.details.setWordWrap(True);column.addWidget(self.details)
        row.addLayout(column,1)
        self.warning=QLabel();self.warning.setWordWrap(True);self.warning.setMaximumWidth(310);self.warning.setStyleSheet('color:#f3c66a;');row.addWidget(self.warning)
        button=QPushButton('环境与天气');button.clicked.connect(self.open_environment);row.addWidget(button)
        window.client.state_received.connect(self.update_state)
        window.client.connection_changed.connect(lambda connected,_:None if connected else self.disconnected())
        self.disconnected()
        self.rating_timer=QTimer(self);self.rating_timer.setInterval(1000);self.rating_timer.timeout.connect(self.refresh_rating);self.rating_timer.start()

    def disconnected(self):
        self.advice.reset();self.rating_model.reset();self.rating.setText('运行评估 · 未评估');self.hardware.setText('运行主机 · 未连接，硬件统计不可用')
        self.details.setText('连接后显示实际显卡、UE 显存与驱动预算、CPU / 内存及实测帧率。')
        self.warning.clear();self.hardware.setToolTip('')

    def update_state(self,state):
        data=state.get('runtime_hardware',{})
        if not data:
            self.disconnected();self.hardware.setText('当前 UE 版本未提供硬件统计，请使用新版仿真。');return
        used,budget=number(data,'ue_vram_used_bytes'),number(data,'ue_vram_budget_bytes')
        total=number(data,'gpu_dedicated_total_bytes');fps=number(data,'ue_fps')
        self.hardware.setText(f"{data.get('gpu_name','显卡未提供')}  ·  显卡专用显存 {gib(total)}  ·  UE 使用 {gib(used)} / 驱动预算 {gib(budget)}")
        self.details.setText(f"运行主机 CPU {percent(number(data,'system_cpu_pct'))}  ·  UE GPU 引擎峰值 {percent(number(data,'ue_gpu_engine_peak_pct'))}  ·  系统内存 {gib(number(data,'system_ram_used_bytes'))} / {gib(number(data,'system_ram_total_bytes'))}  ·  UE {'未提供' if fps is None else f'{fps:.1f} FPS'}")
        self.hardware.setToolTip(f"仿真运行主机：{data.get('cpu_name','未知 CPU')}\nUE 进程内存：{gib(number(data,'ue_ram_bytes'))}\n显存使用与预算来自 UE RHI；预算不是显卡物理容量。\nGPU 百分比为此 UE 进程最忙引擎的 Windows 计数器读数，不是整卡总占用。")
        preparing=state.get('world_streaming_ready') is False or state.get('population',{}).get('pending',False)
        self.warning.setText(self.advice.update(data,preparing=preparing))
        self.rating_model.update(data,state.get('performance_profile','economy'),preparing=preparing);self.refresh_rating()

    def refresh_rating(self):
        grade,reason=self.rating_model.current()
        self.rating.setText('运行评估 · '+grade);self.rating.setToolTip(reason+'；基于当前档位的滚动样本，不是硬件跑分或整城保证。')
        color={'良好':'#76d6a0','一般':'#e6b76c','较差':'#f08080'}.get(grade,'#a2adbd')
        self.rating.setStyleSheet('color:'+color+';');self.rating_changed.emit(grade,reason,color)

    def open_environment(self):
        if self.dialog is None:self.dialog=EnvironmentDialog(self.window)
        self.dialog.show();self.dialog.raise_();self.dialog.activateWindow()


class EnvironmentDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.pending=None;self.dirty=False;self.actual=None
        self.setWindowTitle('环境与天气');self.resize(540,410)
        layout=QVBoxLayout(self)
        hint=QLabel('作用于整个场景，本次运行有效。调整时间改变太阳与天空光照；雾和雨为视觉效果，不自动改变风力、飞行动力或真实红外温度。');hint.setWordWrap(True);layout.addWidget(hint)
        form=QFormLayout();self.time_override=QCheckBox('使用指定时间的光照');form.addRow(self.time_override)
        self.hour=QTimeEdit(QTime(12,0));self.hour.setDisplayFormat('HH:mm');form.addRow('场景时间',self.hour)
        self.fog=QSpinBox();self.fog.setRange(0,100);self.fog.setSuffix(' %');self.fog.setToolTip('雾沿观察距离衰减对比度：近处影响较小，远处目标更难辨认；不改变镜头焦点。');form.addRow('雾强度',self.fog)
        self.rain=QSpinBox();self.rain.setRange(0,100);self.rain.setSuffix(' %');form.addRow('雨强度',self.rain)
        self.clouds=QSpinBox();self.clouds.setRange(0,100);self.clouds.setSuffix(' %');form.addRow('云量 · 0关闭附加云层',self.clouds)
        self.clouds.setToolTip('UE 实际体积云，可见光与楼宇红外共用。增加 GPU 开销；红外为灰度外观代理，夜间未标定。')
        layout.addLayout(form)
        presets=QHBoxLayout();self.presets=[]
        for text,fog,rain,clouds in [('晴朗',0,0,0),('多云',0,0,65),('大雾',80,0,0),('下雨',15,70,75)]:
            button=QPushButton(text);button.clicked.connect(lambda _,f=fog,r=rain,c=clouds:self.preset(f,r,c));presets.addWidget(button);self.presets.append(button)
        layout.addLayout(presets)
        self.status=QLabel('请连接新版 UE，等待环境能力回读。');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();self.apply=QPushButton('应用环境');self.apply.setObjectName('primary');self.reset=QPushButton('恢复场景默认');row.addWidget(self.apply);row.addWidget(self.reset);layout.addLayout(row)
        self.apply.clicked.connect(lambda:self.submit(False));self.reset.clicked.connect(lambda:self.submit(True))
        for signal in (self.time_override.toggled,self.hour.timeChanged,self.fog.valueChanged,self.rain.valueChanged,self.clouds.valueChanged):signal.connect(self.mark_dirty)
        window.client.state_received.connect(self.update_state)
        window.client.request_completed.connect(self.completed);window.client.request_failed.connect(self.failed)
        window.client.connection_changed.connect(lambda connected,_:None if connected else self.disconnected())
        self.update_state(window.state)

    def mark_dirty(self,*_):self.dirty=True;self.status.setText('有未应用的环境修改');self.controls()
    def preset(self,fog,rain,clouds=0):
        self.fog.setValue(fog if self.actual and self.actual.get('fog_supported') else 0)
        self.rain.setValue(rain if self.actual and self.actual.get('rain_supported') else 0)
        self.clouds.setValue(clouds if self.actual and self.actual.get('clouds_supported') else 0)
        self.mark_dirty()
    def controls(self):
        available=self.window.client.ready and self.actual is not None
        editable=available and self.pending is None
        self.apply.setEnabled(available and self.dirty and self.pending is None)
        self.reset.setEnabled(available and self.pending is None)
        self.time_override.setEnabled(editable and self.actual.get('time_supported',False))
        self.hour.setEnabled(self.time_override.isEnabled() and self.time_override.isChecked())
        self.fog.setEnabled(editable and self.actual.get('fog_supported',False));self.rain.setEnabled(editable and self.actual.get('rain_supported',False))
        self.clouds.setEnabled(editable and self.actual.get('clouds_supported',False))
        for button in self.presets:button.setEnabled(editable)
    def values(self):
        value=self.hour.time()
        result=dict(time_override=self.time_override.isChecked(),hour=value.hour()+value.minute()/60.,fog=self.fog.value()/100.,rain=self.rain.value()/100.)
        if self.actual and self.actual.get('clouds_supported'):result['clouds']=self.clouds.value()/100.
        return result
    def fill(self,data):
        minutes=round(data.get('hour',12)*60)%1440
        blocker=QSignalBlocker(self.clouds);self.clouds.setValue(round(data.get('clouds',0)*100));del blocker
        for widget,value,method in [(self.time_override,data.get('time_override',False),'setChecked'),(self.hour,QTime(minutes//60,minutes%60),'setTime'),(self.fog,round(data.get('fog',0)*100),'setValue'),(self.rain,round(data.get('rain',0)*100),'setValue')]:
            blocker=QSignalBlocker(widget);getattr(widget,method)(value);del blocker
    def update_state(self,state):
        if getattr(self,'run_id',None) and state.get('run_id')!=self.run_id:self.pending=None;self.dirty=False
        self.run_id=state.get('run_id');self.actual=state.get('environment')
        self.rain.setToolTip((self.actual or {}).get('rain_unavailable_reason','') or '当前场景雨量；只控制视觉粒子，不模拟降雨动力学。')
        if self.actual is not None and not self.dirty and self.pending is None:
            self.fill(self.actual)
            self.status.setText('已读取实际环境 · 本次运行有效' + ('；本场景无时间光照接口' if not self.actual.get('time_supported') else '') + ('；雨效不可用' if not self.actual.get('rain_supported') else ''))
            if self.actual.get('rain',0)>0 and self.actual.get('rain_supported'):
                self.status.setText(self.status.text()+('；雨效运行中' if self.actual.get('rain_active_streaks',0)>0 or self.actual.get('rain_active_particles',0)>0 else '；雨量已设置，等待雨效画面'))
        self.controls()
    def submit(self,reset):
        if self.pending is not None:return
        command='environment.reset' if reset else 'environment.configure'
        request=self.window.client.request(command,{} if reset else self.values())
        if request:self.pending=request;self.status.setText('等待 UE 应用并确认…')
        self.controls()
    def completed(self,request,command,payload,state):
        if request!=self.pending:return
        self.pending=None;self.dirty=False;self.update_state(state);self.status.setText('环境已生效 · 本次运行有效')
    def failed(self,request,command,payload,message):
        if request!=self.pending:return
        self.pending=None;self.status.setText('应用未确认：'+message);self.controls()
    def disconnected(self):
        self.pending=None;self.actual=None;self.status.setText('连接已断开，环境状态不可用');self.controls()
