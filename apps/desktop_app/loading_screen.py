"""Real loading stages, with a small animated region and no extra 3D view."""
import time
from PySide6.QtCore import Qt,QTimer,QEvent,QRectF
from PySide6.QtGui import QPainter,QColor,QLinearGradient,QPen
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame

class LoadingPulse(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedSize(300,8);self.position=0
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent,True)
        self.setAccessibleName('加载活动指示，不代表百分比')
        self.timer=QTimer(self);self.timer.setInterval(80);self.timer.timeout.connect(self.advance)
    def advance(self):self.position=(self.position+11)%370;self.update()
    def showEvent(self,event):super().showEvent(event);self.timer.start()
    def hideEvent(self,event):self.timer.stop();super().hideEvent(event)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#243348'));x=self.position-70
        g=QLinearGradient(x,0,x+70,0);g.setColorAt(0,QColor('#243348'));g.setColorAt(.6,QColor('#5399ff'));g.setColorAt(1,QColor('#b5e4ff'))
        p.fillRect(QRectF(x,0,70,8),g)

class LoadingScreen(QWidget):
    def __init__(self,w):
        super().__init__(w.centralWidget());self.w=w;self.active=False;self.failed=False;self.target=None;self.old_run=None;self.stage=None
        self.setObjectName('loadingScreen');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.setStyleSheet('#loadingScreen {background:#0c111a;} QLabel {background:transparent;} #loadingCard {background:#131d2b;border:1px solid #2b405c;border-radius:12px;}')
        layout=QVBoxLayout(self);layout.setContentsMargins(42,30,42,30)
        row=QHBoxLayout();brand=QLabel('WISEYE  /  SIMULATION STUDIO');brand.setStyleSheet('color:#82b7ff;font-size:17px;');row.addWidget(brand);row.addStretch();self.elapsed=QLabel();row.addWidget(self.elapsed);layout.addLayout(row)
        layout.addStretch(2);self.scene=QLabel();self.scene.setStyleSheet('color:#849bb9;font-size:15px;');layout.addWidget(self.scene)
        self.title=QLabel('正在构建观测现场');self.title.setWordWrap(True);self.title.setStyleSheet('color:#eef5ff;font-size:36px;font-weight:600;');layout.addWidget(self.title)
        subtitle=QLabel('城市 · 目标 · 多源感知');subtitle.setStyleSheet('color:#627c9d;font-size:18px;');layout.addWidget(subtitle);layout.addSpacing(24)
        card=QFrame();card.setObjectName('loadingCard');card.setMaximumWidth(720);body=QVBoxLayout(card);body.setContentsMargins(24,22,24,22)
        self.stage_label=QLabel();self.stage_label.setStyleSheet('color:#bed9ff;font-size:18px;');body.addWidget(self.stage_label)
        self.detail=QLabel();self.detail.setWordWrap(True);self.detail.setStyleSheet('color:#8da0b9;');body.addWidget(self.detail)
        body.addSpacing(14);self.pulse=LoadingPulse();body.addWidget(self.pulse);body.addSpacing(10)
        steps=QLabel('引擎启动   /   地图流送   /   目标资源   /   设备连接');steps.setWordWrap(True);body.addWidget(steps);layout.addWidget(card);layout.addStretch(3)
        foot=QHBoxLayout();hint=QLabel('首次运行需准备资源缓存。加载期间可返回工作台查看日志。');hint.setWordWrap(True);foot.addWidget(hint,1)
        background=QPushButton('返回工作台');background.clicked.connect(self.hide);foot.addWidget(background);layout.addLayout(foot)
        self.badge=QPushButton('场景加载中…');self.badge.clicked.connect(self.reveal);w.statusBar().addPermanentWidget(self.badge);self.badge.hide()
        self.clock=QTimer(self);self.clock.setInterval(1000);self.clock.timeout.connect(self.tick)
        w.centralWidget().installEventFilter(self);w.client.state_received.connect(self.observe);w.air_client.state_received.connect(lambda _:self.observe(w.state));self.hide()
    def paintEvent(self,event):
        super().paintEvent(event);p=QPainter(self);p.setPen(QPen(QColor('#152437'),1))
        for i in range(8):
            x=self.width()-360+i*50;p.drawLine(x,70,x-140,self.height()-90)
        p.setPen(QColor('#192c43'));font=p.font();font.setPixelSize(min(360,self.height()//2));font.setBold(True);p.setFont(font)
        p.drawText(self.rect().adjusted(0,0,-35,-70),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignBottom,'W')
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.Resize:self.setGeometry(obj.rect())
        return False
    def begin(self,scene,switch=False):
        self.w.clear_gimbal_input();self.w.manual_keys.clear();self.w.stop_manual_input()
        if hasattr(self.w,'mission_workspace'):self.w.mission_workspace.stop_keys()
        self.active=True;self.failed=False;self.target=scene.get('id');self.old_run=self.w.state.get('run_id') if switch else None
        self.started=time.monotonic();self.ready_stamps=set();self.scene.setText(scene.get('name') or self.target or 'WISEYE');self.title.setText('正在构建观测现场')
        self.pulse.show();self.clock.start();self.badge.show();self.phase('map' if switch else 'engine','正在切换地图…' if switch else '正在启动仿真进程…');self.reveal()
    def reveal(self):
        if self.active or self.failed:self.setGeometry(self.parentWidget().rect());self.show();self.raise_()
    def phase(self,stage,detail):
        if not self.active:return
        self.stage=stage;self.stage_label.setText({'engine':'01 / 启动引擎','map':'02 / 装载地图','population':'03 / 准备目标资源','devices':'04 / 连接设备'}.get(stage,stage))
        self.detail.setText(detail);self.badge.setText('加载中 · '+self.stage_label.text().split(' / ')[-1]);self.tick()
    def tick(self):
        if self.active:self.elapsed.setText(f'{int(time.monotonic()-self.started)} s')
    def observe(self,state):
        if not self.active:return
        if state.get('scene_id')!=self.target or (self.old_run and state.get('run_id')==self.old_run):return
        data=state.get('runtime_hardware',{});pop=state.get('population',{})
        for spawner in pop.get('spawners',[]):
            if spawner.get('preload_error'):self.fail('人车资源预载失败：'+spawner['preload_error']);return
        if state.get('world_streaming_ready') is False:
            self.ready_stamps.clear();self.phase('map','正在流送设备附近的道路、建筑与场景资源…')
        elif pop.get('pending') or data.get('asset_compile_jobs',0)>0 or data.get('shader_compile_jobs',0)>0:
            self.ready_stamps.clear();self.phase('population','正在预载人车资源、准备材质并创建场景目标…')
        elif not self.w.air_client.ready:self.phase('devices','地图已就绪，正在同步飞控与设备数据…')
        elif self.w.client.ready and state.get('devices'):
            if 'sample_time_s' in data:
                gallery=self.w.gallery
                displayed=gallery.displayed()
                if displayed and not any(k in gallery.frames and k not in gallery.messages for k in displayed):
                    self.phase('devices','正在初始化首帧画面…');return
                self.ready_stamps.add(data['sample_time_s'])
                if len(self.ready_stamps)<3:self.phase('devices','首帧已到达，正在确认资源准备完成…');return
            self.finish()
    def finish(self):
        self.active=False;self.failed=False;self.clock.stop();self.hide();self.badge.hide()
    def fail(self,message):
        if not self.active:return
        self.active=False;self.failed=True;self.clock.stop();self.title.setText('场景尚未就绪');self.detail.setText(message);self.pulse.hide();self.badge.setText('加载未完成 · 查看原因');self.reveal()
    def stopped(self):
        if self.active:self.finish()
    def showEvent(self,event):
        super().showEvent(event)
        if self.active:self.pulse.timer.start();self.clock.start();self.tick()
    def hideEvent(self,event):self.pulse.timer.stop();self.clock.stop();super().hideEvent(event)
