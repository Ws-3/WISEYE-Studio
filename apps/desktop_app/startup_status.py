"""Display the owning preview supervisor's startup stages without blocking Qt."""
import json
import os
from pathlib import Path
from PySide6.QtCore import QTimer


class StartupStatus:
    def __init__(self,window,path):
        self.window=window;self.path=Path(path);self.last=None
        self.timer=QTimer(window);self.timer.setInterval(400)
        self.timer.timeout.connect(self.poll);self.timer.start();self.poll()

    def poll(self):
        try:item=json.loads(self.path.read_text(encoding='utf8'))
        except (OSError,ValueError):return
        stage=item.get('stage');message=item.get('message','')
        if stage not in ('loading','flight','assets','ready','failed'):return
        if stage==self.last:return
        self.last=stage;w=self.window
        w.log(message);w.connection_detail.setText(message);w.statusBar().showMessage(message)
        w.badge.setText({'loading':'UE 启动中','flight':'飞控初始化','assets':'准备材质缓存','ready':'正在连接','failed':'启动失败'}[stage])
        w.quick_connect.setEnabled(stage=='failed')
        if stage in ('loading','flight','assets'):
            w.quick_connect.setText('正在启动…')
        else:
            w.sync_session_buttons();self.timer.stop()
            if stage=='failed':w.badge.setText('启动失败 · 连接')
            if stage=='ready' and not w.client.ready:w.connect_ue()


def watch_startup(window):
    path=os.environ.get('WISEYE_SESSION_STATUS')
    if path:window.startup_status=StartupStatus(window,path)
