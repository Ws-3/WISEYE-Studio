"""Compact live machine status and a correlated environment control dialog."""
from PySide6.QtCore import QTime, QSignalBlocker
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDialog,
    QFormLayout,QCheckBox,QTimeEdit,QSpinBox)
from core.runtime_metrics import PerformanceAdvice,number


def gib(value):return '未提供' if value is None else f'{value/1024**3:.2f} GiB'
def percent(value):return '未提供' if value is None else f'{value:.0f}%'


class RuntimePanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.advice=PerformanceAdvice();self.dialog=None
        row=QHBoxLayout(self);row.setContentsMargins(10,4,10,4)
        column=QVBoxLayout();column.setSpacing(2)
        self.hardware=QLabel();self.hardware.setWordWrap(True);column.addWidget(self.hardware)
        self.details=QLabel();self.details.setObjectName('muted');self.details.setWordWrap(True);column.addWidget(self.details)
        row.addLayout(column,1)
        self.warning=QLabel();self.warning.setWordWrap(True);self.warning.setMaximumWidth(310);self.warning.setStyleSheet('color:#f3c66a;');row.addWidget(self.warning)
        button=QPushButton('环境与天气');button.clicked.connect(self.open_environment);row.addWidget(button)
        window.client.state_received.connect(self.update_state)
        window.client.connection_changed.connect(lambda connected,_:None if connected else self.disconnected())
        self.disconnected()

    def disconnected(self):
        self.advice.reset();self.hardware.setText('运行主机 · 未连接，硬件统计不可用')
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
        self.warning.setText(self.advice.update(data))

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
        self.fog=QSpinBox();self.fog.setRange(0,100);self.fog.setSuffix(' %');form.addRow('雾强度',self.fog)
        self.rain=QSpinBox();self.rain.setRange(0,100);self.rain.setSuffix(' %');form.addRow('雨强度',self.rain)
        layout.addLayout(form)
        presets=QHBoxLayout();self.presets=[]
        for text,fog,rain in [('晴朗',0,0),('大雾',80,0),('下雨',15,70)]:
            button=QPushButton(text);button.clicked.connect(lambda _,f=fog,r=rain:self.preset(f,r));presets.addWidget(button);self.presets.append(button)
        layout.addLayout(presets)
        self.status=QLabel('请连接新版 UE，等待环境能力回读。');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();self.apply=QPushButton('应用环境');self.apply.setObjectName('primary');self.reset=QPushButton('恢复场景默认');row.addWidget(self.apply);row.addWidget(self.reset);layout.addLayout(row)
        self.apply.clicked.connect(lambda:self.submit(False));self.reset.clicked.connect(lambda:self.submit(True))
        for signal in (self.time_override.toggled,self.hour.timeChanged,self.fog.valueChanged,self.rain.valueChanged):signal.connect(self.mark_dirty)
        window.client.state_received.connect(self.update_state)
        window.client.request_completed.connect(self.completed);window.client.request_failed.connect(self.failed)
        window.client.connection_changed.connect(lambda connected,_:None if connected else self.disconnected())
        self.update_state(window.state)

    def mark_dirty(self,*_):self.dirty=True;self.status.setText('有未应用的环境修改');self.controls()
    def preset(self,fog,rain):
        self.fog.setValue(fog if self.actual and self.actual.get('fog_supported') else 0)
        self.rain.setValue(rain if self.actual and self.actual.get('rain_supported') else 0)
        self.mark_dirty()
    def controls(self):
        available=self.window.client.ready and self.actual is not None
        editable=available and self.pending is None
        self.apply.setEnabled(available and self.dirty and self.pending is None)
        self.reset.setEnabled(available and self.pending is None)
        self.time_override.setEnabled(editable and self.actual.get('time_supported',False))
        self.hour.setEnabled(self.time_override.isEnabled() and self.time_override.isChecked())
        self.fog.setEnabled(editable and self.actual.get('fog_supported',False));self.rain.setEnabled(editable and self.actual.get('rain_supported',False))
        for button in self.presets:button.setEnabled(editable)
    def values(self):
        value=self.hour.time()
        return dict(time_override=self.time_override.isChecked(),hour=value.hour()+value.minute()/60.,fog=self.fog.value()/100.,rain=self.rain.value()/100.)
    def fill(self,data):
        minutes=round(data.get('hour',12)*60)%1440
        for widget,value,method in [(self.time_override,data.get('time_override',False),'setChecked'),(self.hour,QTime(minutes//60,minutes%60),'setTime'),(self.fog,round(data.get('fog',0)*100),'setValue'),(self.rain,round(data.get('rain',0)*100),'setValue')]:
            blocker=QSignalBlocker(widget);getattr(widget,method)(value);del blocker
    def update_state(self,state):
        if getattr(self,'run_id',None) and state.get('run_id')!=self.run_id:self.pending=None;self.dirty=False
        self.run_id=state.get('run_id');self.actual=state.get('environment')
        if self.actual is not None and not self.dirty and self.pending is None:
            self.fill(self.actual)
            self.status.setText('已读取实际环境 · 本次运行有效' + ('；本场景无时间光照接口' if not self.actual.get('time_supported') else '') + ('；雨效不可用' if not self.actual.get('rain_supported') else ''))
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
