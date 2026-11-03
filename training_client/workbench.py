"""Three-view training workspace styled with WISEYE's simulator theme."""
import time
from collections import deque
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QFont
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QFrame, QVBoxLayout,
    QHBoxLayout, QFormLayout, QSplitter, QScrollArea, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QSlider, QFileDialog, QDoubleSpinBox, QComboBox)
from .client import Client
from .fusion import decode, blend_pair, comparison
from .view import controls, EnlargedView
from .theme import STYLE


def label(text, name=''):
    item=QLabel(text)
    if name:item.setObjectName(name)
    return item


class Tile(QFrame):
    def __init__(self,title,channel):
        super().__init__()
        from .preview import Canvas
        self.setObjectName('viewTile');layout=QVBoxLayout(self)
        layout.setContentsMargins(10,8,10,8);layout.setSpacing(6)
        row=QHBoxLayout();row.addWidget(label(channel,'channel'));row.addWidget(label(title,'tileTitle'));row.addStretch()
        self.badge=label('未连接','muted');row.addWidget(self.badge);layout.addLayout(row)
        self.canvas=Canvas();self.canvas.setMinimumSize(200,130);layout.addWidget(self.canvas,1)
        self.meta=label('—','streamMeta')
        tools=QHBoxLayout();tools.setContentsMargins(0,0,0,0);tools.addWidget(self.meta,1)
        tools.addLayout(controls(self.canvas));enlarge=QPushButton('放大');enlarge.setObjectName('imageTool');tools.addWidget(enlarge)
        self.tools_widget=QWidget();self.tools_widget.setLayout(tools);layout.addWidget(self.tools_widget)
        self.title=title;self.popup=None;enlarge.clicked.connect(self.enlarge);self.canvas.activated.connect(self.enlarge)

    def enlarge(self):
        if self.popup is None:
            self.popup=EnlargedView(self.title,self.canvas,self)
            self.popup.destroyed.connect(lambda:self.popup_closed())
        self.popup.show();self.popup.raise_();self.popup.activateWindow()

    def popup_closed(self):self.popup=None

    def clear(self,message='等待数据'):
        self.canvas.image=QImage();self.canvas.message=message;self.canvas.update()
        self.badge.setText('未就绪');self.meta.setText('—')


class Window(QWidget):
    def __init__(self,args):
        super().__init__()
        from .preview import ensure_fonts
        ensure_fonts();QApplication.instance().setFont(QFont('Microsoft YaHei UI',10))
        self.setObjectName('appRoot');self.setStyleSheet(STYLE+'\nQCheckBox { background: transparent; }\nQSlider { background: transparent; }')
        self.setWindowTitle('WISEYE Training · 多源数据与融合工作台');self.resize(1450,960)
        self._closing=False;self.decoded={}
        self.worker=None;self.last_frame_at=0;self.latest=None;self.received=0
        self._restart_requested=False;self._stopping=False
        self.source_timer=QTimer(self);self.source_timer.setSingleShot(True);self.source_timer.setInterval(250)
        self.source_timer.timeout.connect(self.restart_sources)
        self.rate_events=deque()
        from .layout_v4 import build
        build(self,args)
        self.freshness=QTimer(self);self.freshness.timeout.connect(self.check_freshness);self.freshness.start(500)
        self.frame_timer=QTimer(self);self.frame_timer.timeout.connect(self.poll_frame);self.frame_timer.start(33)

    def browse(self):
        path=QFileDialog.getExistingDirectory(self,'训练样本目录',self.directory.text())
        if path:self.directory.setText(path);self.change_settings()

    def change_settings(self,*_):
        self.directory.setToolTip(self.directory.text().strip())
        if not self.worker:return
        policy=dict(keep_partial_occlusion=self.occlusion.isChecked(),keep_partial_outside=self.outside.isChecked(),max_fps=10)
        self._settings_revision=self.worker.update_settings(policy,self.directory.text().strip())
        self.settings_status.setText('采集设置已更新，将从后续新样本生效')

    def settings_confirmed(self,revision):
        if revision==getattr(self,'_settings_revision',0):self.settings_status.setText('当前采集设置已应用')

    def source_changed(self,*_):
        if not self.visible.isChecked() and not self.infrared.isChecked():
            sender=self.sender();sender.blockSignals(True);sender.setChecked(True);sender.blockSignals(False)
            self.state.setText('至少保留一路数据源');return
        if self.worker:self.source_timer.start()

    def restart_sources(self):
        if self.worker:
            self._restart_requested=True;self.stop(preserve_restart=True)

    def start(self):
        if self.worker:self.restart_sources();return
        self._start()

    def _start(self):
        from .preview import Receiver
        if self.worker:return
        self._stopping=False;self._restart_requested=False
        sensors=[sensor for sensor,enabled in [('visible',self.visible.isChecked()),('infrared',self.infrared.isChecked())] if enabled]
        if not sensors:self.state.setText('请选择至少一路数据源');return
        self.latest=None;self.last_frame_at=0;self.received=0;self.rate_events.clear();self.clear_tiles('连接中…')
        client=Client(self.host.text().strip(),self.port.value(),self.device.text().strip())
        policy=dict(keep_partial_occlusion=self.occlusion.isChecked(),keep_partial_outside=self.outside.isChecked(),max_fps=10)
        self.worker=Receiver(client,policy,self.directory.text(),sensors,self.display_fps.value(),self.save_fps.value(),self.record.isChecked())
        self.worker.latest_only=True
        self.worker.status.connect(self.show_error);self.worker.finished.connect(self.stopped)
        self.worker.metrics.connect(self.show_metrics)
        self.worker.settings_applied.connect(self.settings_confirmed);self._settings_revision=0
        self.change_rates()
        for item in self.inputs:item.setEnabled(False)
        self.connect.setText('应用连接设置')
        self.disconnect.setEnabled(True);self.badge.setText('连接中');self.worker.start()

    def show_frame(self,bundle):
        if self._stopping:return
        self.latest=bundle
        try:self.decoded=bundle.get('_images') or {sensor:decode(packet) for sensor,packet in bundle['samples'].items()}
        except (ValueError,KeyError) as error:self.show_error(str(error));return
        self.last_frame_at=time.monotonic();self.received+=1
        self.counter.setText(f'已接收 {self.received} 组');self.redraw()

    def change_rates(self,*_):
        from .layout_v4 import update_save_state
        if hasattr(self,'save_action'):update_save_state(self)
        if self.worker:
            self.worker.rates.configure(self.display_fps.value(),self.save_fps.value(),self.record.isChecked())

    def poll_frame(self):
        if self.worker and not self._stopping:
            bundle=self.worker.take_frame()
            if bundle is not None:self.show_frame(bundle)

    def show_metrics(self,item):
        if self._stopping:return
        self.rate_events.append(item)
        while self.rate_events and item['at']-self.rate_events[0]['at']>5:self.rate_events.popleft()
        def rate(key):
            values=[i['at'] for i in self.rate_events if i[key]]
            return f'{(len(values)-1)/(values[-1]-values[0]):.2f} FPS' if len(values)>1 and values[-1]>values[0] else '—'
        self.actual_rates.setText(f"实测预览 {rate('displayed')} · 保存 {rate('did_save').replace('FPS','组/s')}")
        self.counter.setText(f"接收 {item['received']} 组 · 保存 {item['saved']} 组")
        from .layout_v4 import update_save_state
        update_save_state(self,item['did_save'])

    def redraw(self,*_):
        from .preview import draw_gt
        self.alpha_label.setText(f'红外占比 {self.alpha.value()}%')
        if not self.latest:return
        self.badge.setText('同步样本已连接')
        samples=self.latest['samples']
        try:
            for sensor in ('visible','infrared'):
                tile=self.tiles[sensor]
                if sensor not in samples:tile.clear('未订阅此数据源');continue
                packet=samples[sensor];image=self.decoded[sensor]
                tile.canvas.image=draw_gt(image,packet) if self.show_gt.isChecked() else image;tile.canvas.update()
                tile.badge.setText('负样本' if packet['negative_sample'] else '有效标注' if packet['training_eligible'] else '策略忽略')
                tile.meta.setText(f"{packet['width']}×{packet['height']}  ·  GT {len(packet['objects'])}  ·  帧 {packet['frame_number']}")
            fusion=self.tiles['fusion']
            if len(samples)==2:
                try:
                    mode=self.fusion_mode.currentData()
                    image=blend_pair(self.latest,self.alpha.value()/100,mode,images=self.decoded)
                    fusion.canvas.image=draw_gt(image,samples['infrared']) if self.show_gt.isChecked() else image;fusion.canvas.update()
                    stats=comparison(self.latest,mode)
                    timing='—' if stats['request_round_trip_ms'] is None else f"{stats['request_round_trip_ms']:.1f} ms"
                    differences=stats['gt_center_differences']
                    detail='无共同可见目标' if not differences else '\n'.join(f"{o['target_id']} Δx {o['dx_px']:+.1f} / Δy {o['dy_px']:+.1f} px · {o['distance_px']:.1f} px" for o in differences)
                    self.comparison.setText(f"采集时差(仿真) {stats['capture_delta_ms']:+.3f} ms · 取帧耗时 {timing} · 基线 {stats['baseline_cm']:.2f} cm\nGT中心差：{detail}")
                    fusion.badge.setText('原始叠加' if mode=='raw' else '旋转已补偿')
                    fusion.meta.setText(f"Δt {stats['capture_delta_ms']:+.3f} ms · 取帧 {timing} · IR网格 · 基线视差未补偿")
                except ValueError as error:fusion.clear(str(error))
            else:fusion.clear('同时订阅可见光与红外后显示融合')
            first=next(iter(samples.values()))
            identity=self.latest.get('pair_id',first.get('sample_token','—'))
            self.state.setText(f"同组身份：{first['run_id'][:8]} / {first['device_id']} / {str(identity)[:12]}  ·  仿真时间 {first['simulation_time_s']:.3f}s  ·  {'双路同刻样本' if len(samples)==2 else '单路样本'}")
        except (ValueError,KeyError) as error:self.show_error(str(error))

    def clear_tiles(self,message):
        for tile in self.tiles.values():tile.clear(message)
        self.comparison.setText('采集时差 —\n取帧耗时 —\nGT中心差 —')

    def show_error(self,message):
        if self._stopping:return
        self.latest=None
        self.decoded={};self.clear_tiles('等待有效新数据');self.badge.setText('样本不可用')
        self.state.setText('标注采集正在重试：'+message)
        if self.record.isChecked():self.saving_state.setText('采集异常 · 保存未确认')

    def check_freshness(self):
        if self.worker and self.latest and time.monotonic()-self.last_frame_at>max(3,3/self.display_fps.value()):self.show_error('超过显示周期未收到新样本')

    def stop(self,preserve_restart=False):
        if not preserve_restart:self._restart_requested=False
        self.source_timer.stop();self._stopping=True;self.latest=None;self.decoded={}
        self.clear_tiles('正在切换数据源…' if self._restart_requested else '正在断开…')
        if self.worker:self.worker.stop_event.set();self.disconnect.setEnabled(False);self.state.setText('正在断开…')

    def stopped(self):
        self.worker.deleteLater();self.worker=None;self.latest=None;self.clear_tiles('未连接')
        for item in self.inputs:item.setEnabled(True)
        self.disconnect.setEnabled(False);self.badge.setText('未连接');self.state.setText('已断开')
        self._stopping=False;self.connect.setText('连接数据')
        from .layout_v4 import update_save_state
        update_save_state(self)
        if self._closing:QTimer.singleShot(0,self.close)
        elif self._restart_requested:QTimer.singleShot(0,self._start)

    def closeEvent(self,event):
        from PySide6.QtCore import QSettings
        QSettings('WISEYE','Training').setValue('v4/split',self.train_split.saveState())
        self.connection_dialog.close()
        if self.worker:
            self._closing=True;self.stop();event.ignore()
            self.setEnabled(False)
            return
        for tile in self.tiles.values():
            if tile.popup:tile.popup.close()
        event.accept()
