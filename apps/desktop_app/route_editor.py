"""Single-drone waypoint editor with an equal-scale XY canvas and Z table."""
import math
import copy
from PySide6.QtCore import Qt, QPointF, QSignalBlocker
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QDoubleSpinBox,QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QFileDialog,QHeaderView,QSplitter)
from core.config import ROOT
from core.routes import validate_route,load_route,save_route


class RouteCanvas(QWidget):
    def __init__(self,editor):
        super().__init__()
        self.editor=editor
        self.setMinimumSize(300,230)
        self.drag=-1
        self.transform=None

    def points(self):
        try:return self.editor.points()
        except ValueError:return []

    def paintEvent(self,_):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor('#121923'))
        painter.setPen(QPen(QColor('#253142'),1))
        for x in range(0,self.width(),25):painter.drawLine(x,0,x,self.height())
        for y in range(0,self.height(),25):painter.drawLine(0,y,self.width(),y)
        points=self.points()
        if not points:return
        if self.drag<0 or self.transform is None:
            xs,ys=[p[0] for p in points],[p[1] for p in points]
            cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
            scale=min((self.width()-60)/max(10,max(ys)-min(ys)),(self.height()-60)/max(10,max(xs)-min(xs)))
            self.transform=(cx,cy,scale)
        painter.setPen(QColor('#b4bcc8'))
        painter.drawText(12,20,'俯视 XY · 拖动航点修改水平位置 · 高度在表格设置')
        painter.setPen(QPen(QColor('#78b1ff'),2))
        pixels=[self.pixel(p) for p in points]
        for a,b in zip(pixels,pixels[1:]):painter.drawLine(a,b)
        for index,p in enumerate(pixels):
            painter.setBrush(QColor('#f3c66a') if index==self.editor.table.currentRow() else QColor('#78b1ff'))
            painter.drawEllipse(p,6,6)
            painter.drawText(p+QPointF(9,-8),f'{index+1}  Z {points[index][2]:.1f} m')

    def pixel(self,point):
        cx,cy,s=self.transform
        return QPointF(self.width()/2+(point[1]-cy)*s,self.height()/2-(point[0]-cx)*s)

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton or not self.transform:return
        for index,p in enumerate(self.points()):
            screen=self.pixel(p)
            if math.hypot(screen.x()-event.position().x(),screen.y()-event.position().y())<13:
                self.drag=index;self.editor.table.selectRow(index);return

    def mouseMoveEvent(self,event):
        if self.drag<0:return
        cx,cy,s=self.transform
        x=cx-(event.position().y()-self.height()/2)/s
        y=cy+(event.position().x()-self.width()/2)/s
        blocker=QSignalBlocker(self.editor.table)
        for col,value in ((0,x),(1,y)):
            self.editor.table.item(self.drag,col).setText(f'{value:.3f}')
        del blocker
        self.update()
        self.editor.dirty()

    def mouseReleaseEvent(self,event):
        self.drag=-1
        self.update()


class RouteEditor(QDialog):
    def __init__(self,window):
        super().__init__(window)
        self.window=window
        self.device_id=window.selected_drone
        self.uploaded_snapshot=None
        self.uploading_snapshot=None
        self.scene_id=window.state.get('scene_id') or (window.scenes.currentData() or {}).get('id','original')
        self.setWindowTitle('WISEYE · '+self.device_id+' 航线编辑')
        self.resize(1000,720)
        layout=QVBoxLayout(self)
        row=QHBoxLayout()
        self.name=QLineEdit('自定义航线')
        self.name.setMaxLength(80)
        from apps.desktop_app.ui.components import NumberInput
        self.speed=NumberInput(.2,15,'m/s',2,.1);self.speed.setValue(3)
        self.repeat=QCheckBox('循环执行')
        row.addWidget(QLabel('名称'));row.addWidget(self.name,1);row.addWidget(self.speed);row.addWidget(self.repeat)
        layout.addLayout(row)
        layout.addWidget(QLabel(f'场景 {self.scene_id} · UE 世界坐标（米，Z 向上）· 先起飞；逐点执行，拐点减速；不自动避障'))
        split=QSplitter()
        self.table=QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(['X / m','Y / m','Z / m'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.canvas=RouteCanvas(self)
        split.addWidget(self.table);split.addWidget(self.canvas);split.setSizes([340,600])
        layout.addWidget(split,1)
        row=QHBoxLayout()
        for text,callback in [('增加航点',self.add_point),('删除选中点',self.delete_point),('上移',lambda:self.move(-1)),('下移',lambda:self.move(1)),('用无人机当前位置替换',self.use_position)]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
        layout.addLayout(row)
        row=QHBoxLayout()
        for text,callback in [('打开草稿',self.open_file),('保存草稿',self.save_file),('上传到 '+self.device_id,self.upload),('执行已上传航线',self.start_route),('暂停航线',lambda:self.control('sim.pause')),('继续航线',lambda:self.control('sim.resume')),('停止并悬停',lambda:self.control('route.stop'))]:
            button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
            if text.startswith('上传到'):self.upload_button=button
            if text=='执行已上传航线':self.start_button=button;button.setObjectName('primary');button.setEnabled(False)
        layout.addLayout(row)
        self.status=QLabel('编辑的是草稿，上传不会自动起飞或开始飞行。')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table.itemChanged.connect(lambda *_:(self.canvas.update(),self.dirty()))
        self.table.currentCellChanged.connect(lambda *_:self.canvas.update())
        self.name.textChanged.connect(self.dirty)
        self.speed.valueChanged.connect(self.dirty)
        self.repeat.toggled.connect(self.dirty)
        self.window.air_client.state_received.connect(self.air_state)
        self.window.air_client.failed.connect(self.failed)
        self.window.air_client.completed.connect(self.completed)
        self.window.air_client.connection_changed.connect(self.connection_changed)
        data=window.air_state.get('route')
        if data and data.get('scene_id')==self.scene_id:self.set_data(data);self.uploaded_snapshot=copy.deepcopy(self.data());self.refresh_start()
        else:
            x,y,z=self.current_position()
            z+=3 if window.air_state.get('flight_status')=='ready' else 0
            for p in [[x,y,z],[x+5,y,z],[x+5,y+5,z],[x,y+5,z],[x,y,z]]:self.add_point(p)

    def current_position(self):
        ned=self.window.air_state.get('position_ned_m')
        return [ned[0],ned[1],-ned[2]] if ned else [v/100 for v in self.window.state.get('drone_position_cm',[0,0,300])]

    def points(self):
        try:
            points=[[float(self.table.item(row,col).text()) for col in range(3)] for row in range(self.table.rowCount())]
            if not all(math.isfinite(n) and abs(n)<=100000 for p in points for n in p):raise ValueError()
            return points
        except (ValueError,AttributeError):raise ValueError('请填写完整的数字航点坐标')

    def data(self):
        return validate_route(dict(version=1,scene_id=self.scene_id,name=self.name.text().strip(),frame='ue_world_m',
                                   speed_mps=self.speed.value(),repeat=self.repeat.isChecked(),waypoints=self.points()),self.scene_id)

    def set_data(self,data):
        validate_route(data,self.scene_id)
        self.table.setRowCount(0)
        self.name.setText(data['name']);self.speed.setValue(data['speed_mps']);self.repeat.setChecked(data['repeat'])
        for point in data['waypoints']:self.add_point(point)

    def add_point(self,point=None):
        if isinstance(point,bool) or point is None:
            try:point=self.points()[-1] if self.table.rowCount() else self.current_position()
            except ValueError as exc:self.status.setText(str(exc));return
            point=[point[0]+2,point[1],point[2]]
        if self.table.rowCount()>=128:self.status.setText('最多支持 128 个航点');return
        row=self.table.rowCount();self.table.insertRow(row)
        for col,value in enumerate(point):self.table.setItem(row,col,QTableWidgetItem(f'{value:.3f}'))
        self.table.selectRow(row)
        self.canvas.update()

    def delete_point(self):
        row=self.table.currentRow()
        if row>=0:self.table.removeRow(row);self.canvas.update();self.dirty()

    def move(self,step):
        row=self.table.currentRow();target=row+step
        if row<0 or not 0<=target<self.table.rowCount():return
        try:points=self.points()
        except ValueError as exc:self.status.setText(str(exc));return
        points[row],points[target]=points[target],points[row]
        for index in (row,target):
            for col,value in enumerate(points[index]):self.table.item(index,col).setText(f'{value:.3f}')
        self.table.selectRow(target)

    def use_position(self):
        row=self.table.currentRow()
        if row>=0:
            for col,value in enumerate(self.current_position()):self.table.item(row,col).setText(f'{value:.3f}')

    def dirty(self,*_):
        if hasattr(self,'status'):self.status.setText('草稿已修改；上传后才会替换已上传航线，正在执行的航线保持当前快照。')
        if hasattr(self,'start_button'):self.start_button.setEnabled(False)

    def upload(self):
        try:
            if self.window.selected_drone!=self.device_id:raise ValueError('控制对象已改变，请重新打开该无人机的航线编辑器')
            if self.window.state.get('scene_id')!=self.scene_id:raise ValueError('当前运行场景已改变，请重新打开航线编辑器')
            if not self.window.air_client.ready:raise ValueError('飞控未连接，请先连接再上传')
            if self.uploading_snapshot is not None:raise ValueError('正在上传，请等待确认')
            self.uploading_snapshot=copy.deepcopy(self.data())
            self.upload_button.setEnabled(False)
            self.window.command('route.upload',self.uploading_snapshot)
        except ValueError as exc:self.start_after_upload=False;self.status.setText(str(exc))

    def start_route(self):
        try:
            if self.data()!=self.uploaded_snapshot:raise ValueError('草稿与已上传版本不同，请先上传并等待确认')
            if self.window.air_state.get('flight_status')=='ready':raise ValueError('请先起飞，再执行航线')
            if self.window.air_state.get('flight_mode')=='manual' and self.window.air_state.get('command_active'):
                raise ValueError('请等待起飞或悬停动作结束，再执行航线')
            self.control('route.start')
        except ValueError as exc:self.status.setText(str(exc))

    def completed(self,command,state):
        if state.get('drone_id',self.device_id)!=self.device_id:return
        if command=='route.upload':
            self.uploaded_snapshot=self.uploading_snapshot
            self.uploading_snapshot=None;self.upload_button.setEnabled(True)
            try:unchanged=self.data()==self.uploaded_snapshot
            except ValueError:unchanged=False
            self.refresh_start()
            self.status.setText('上传成功，尚未执行。' if unchanged else '提交的版本已上传；另有未上传草稿。')

    def connection_changed(self,connected,message):
        if not connected:
            self.start_after_upload=False;self.uploaded_snapshot=None;self.uploading_snapshot=None
            self.start_button.setEnabled(False);self.upload_button.setEnabled(True);self.status.setText('飞控已断开；草稿保留，需重新上传确认。')

    def control(self,command):
        if self.window.selected_drone!=self.device_id:self.status.setText('控制对象已改变，请重新打开航线编辑器');return
        self.window.command(command,{'device_id':self.device_id})

    def failed(self,command,message):
        if command.startswith('route.'):
            self.start_after_upload=False;self.uploading_snapshot=None;self.upload_button.setEnabled(True);self.status.setText('航线操作失败：'+message)

    def air_state(self,state):
        if state.get('drone_id',self.device_id)!=self.device_id:return
        self.refresh_start()
        if state.get('active_route_name'):
            statuses={'idle':'待命','running':'执行中','paused':'已暂停','completed':'已完成','stopped':'已停止','failed':'执行失败'}
            status=statuses.get(state.get('route_status'),state.get('route_status',''))
            self.setWindowTitle(f"WISEYE · 航线编辑 · {state['active_route_name']} · {status} · 下一点 {state.get('route_next_waypoint','—')} · 已完成 {state.get('route_loops',0)} 圈")

    def refresh_start(self):
        try:matches=self.data()==self.uploaded_snapshot
        except ValueError:matches=False
        state=self.window.air_state
        ready=(self.window.air_client.ready and state.get('drone_id')==self.device_id
               and state.get('flight_status')!='ready' and not state.get('command_active')
               and self.window.simulation_healthy)
        self.start_button.setEnabled(matches and ready)
        self.start_button.setToolTip('需草稿已上传、无人机已起飞、当前动作已结束且仿真推进正常。')

    def open_file(self):
        path,_=QFileDialog.getOpenFileName(self,'打开航线',str(ROOT/'configs/routes'),'JSON (*.json)')
        if path:
            try:self.set_data(load_route(path,self.scene_id));self.status.setText('航线已读取到草稿，尚未上传。')
            except (ValueError,OSError) as exc:self.status.setText('读取失败：'+str(exc))

    def save_file(self):
        try:data=self.data()
        except ValueError as exc:self.status.setText(str(exc));return
        path,_=QFileDialog.getSaveFileName(self,'保存航线',str(ROOT/'configs/routes'/f'{self.scene_id}.json'),'JSON (*.json)')
        if path:
            try:save_route(path,data);self.status.setText('航线已保存；可随 Git 同步。')
            except OSError as exc:self.status.setText('保存失败：'+str(exc))

    def closeEvent(self,event):
        self.start_after_upload=False
        self.window.air_client.state_received.disconnect(self.air_state)
        self.window.air_client.failed.disconnect(self.failed)
        self.window.air_client.completed.disconnect(self.completed)
        self.window.air_client.connection_changed.disconnect(self.connection_changed)
        self.window.route_editor=None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        super().closeEvent(event)


def open_route_editor(window):
    dialog=getattr(window,'route_editor',None)
    if dialog is not None and dialog.device_id!=window.selected_drone:dialog.close();dialog=None
    if dialog is None or not dialog.isVisible():
        window.route_editor=RouteEditor(window)
    window.route_editor.show();window.route_editor.raise_()
