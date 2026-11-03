"""Immediate, device-addressed sensor switches. Parameter drafts remain intact."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton


class SensorPowerPanel(QWidget):
    def __init__(self, settings):
        super().__init__();self.settings=settings;settings.power_panel=self
        layout=QVBoxLayout(self);layout.setContentsMargins(0,4,0,4)
        self.title=QLabel();layout.addWidget(self.title)
        self.buttons={}
        for sensor,label in [('visible','可见光'),('infrared','红外'),('lidar','雷达'),('event','事件相机')]:
            row=QHBoxLayout();row.addWidget(QLabel({'visible':'VIS · 可见光','infrared':'IR · 热红外','lidar':'LiDAR · 点云','event':'EVT · 事件相机'}[sensor]),1)
            button=QPushButton();button.setMaximumWidth(100);button.clicked.connect(lambda _,s=sensor:settings.submit_power(s))
            row.addWidget(button);self.buttons[sensor]=(button,label)
            layout.addLayout(row)
        hint=QLabel('点击即启停，无需应用参数。只停止此传感器的采集与输出，UE连接、飞行控制和观察视角保持运行。')
        hint.setWordWrap(True);hint.setObjectName('hint');layout.addWidget(hint)
        self.refresh()

    def refresh(self):
        s=self.settings;self.title.setText(s.device_id+' · 采集开关')
        for sensor,(button,label) in self.buttons.items():
            actual=s.panels[sensor]['confirmed'];waiting=any(p['key']==(s.device_id,sensor) for p in s.pending.values())
            ready=s.window.client.ready and s.power_supported and actual is not None
            button.setEnabled(ready and not waiting)
            button.setText('等待…' if waiting else ('停止采集' if actual['enabled'] else '开启采集') if actual else '未确认')
            button.setToolTip('只修改此设备的启用状态，保留参数草稿。' if s.power_supported else '连接支持快捷启停的新版 UE；旧版仍可在参数页应用启停。')
