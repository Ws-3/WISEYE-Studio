"""Instance list and detail editor backed by the existing device draft table."""
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame, QScrollArea)
from core.devices import MODELS


class DeviceCatalog(QWidget):
    def __init__(self, editor):
        super().__init__();self.editor=editor;self.window=editor.window;self.loading=False;self.setMaximumWidth(1250)
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(12)
        # Keep the original table as the one draft owner used by collect/save.
        self.actions={b.text():b for b in editor.findChildren(QPushButton)}
        for b in self.actions.values():b.setParent(self)
        editor.hide()
        header=QFrame();header.setObjectName('sessionBar');bar=QHBoxLayout(header)
        self.summary=QLabel();bar.addWidget(self.summary,1)
        for name in ('新增无人机','新增云台'):bar.addWidget(self.actions[name])
        root.addWidget(header)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['实例 / 稳定 ID','型号','类型','运行状态','初始位置 / m','编辑'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False);self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.table.setMinimumHeight(170);self.table.setMaximumHeight(300);root.addWidget(self.table)
        self.table.currentCellChanged.connect(lambda row,*_:self.select(row))
        self.detail=QFrame();self.detail.setObjectName('card');box=QVBoxLayout(self.detail);box.setContentsMargins(16,14,16,14);box.setSpacing(12)
        title=QHBoxLayout();self.identity=QLabel();self.identity.setObjectName('value');title.addWidget(self.identity,1)
        self.status=QLabel();self.status.setObjectName('muted');title.addWidget(self.status);box.addLayout(title)
        form=QFormLayout();form.setSpacing(10)
        self.name=QLineEdit();form.addRow('显示名称',self.name)
        self.model=QComboBox();form.addRow('设备型号',self.model)
        self.xyz=[];coords=QHBoxLayout()
        for axis in 'XYZ':
            label=QLabel(axis);label.setObjectName('muted');coords.addWidget(label)
            field=QDoubleSpinBox();field.setRange(-100000,100000);field.setDecimals(5);field.setSuffix(' m');field.setSingleStep(.1);coords.addWidget(field,1);self.xyz.append(field)
        form.addRow('初始世界位置',coords)
        self.yaw=QDoubleSpinBox();self.yaw.setRange(-180,180);self.yaw.setDecimals(2);self.yaw.setSuffix(' °');form.addRow('初始偏航',self.yaw)
        self.target=QComboBox();form.addRow('默认跟踪目标',self.target)
        box.addLayout(form)
        self.spec=QLabel();self.spec.setObjectName('telemetry');self.spec.setWordWrap(True);box.addWidget(self.spec)
        note=QLabel('实例 ID 保持稳定；编辑的是初始配置。保存后，新增、删除和型号变更需加载场景生效。定位操作只选择现有设备，不移动设备。')
        note.setObjectName('hint');note.setWordWrap(True);box.addWidget(note)
        row=QHBoxLayout();place=QPushButton('在场景中放置');place.clicked.connect(self.place);row.addWidget(place)
        self.parameters=QPushButton('传感器参数');self.parameters.clicked.connect(self.open_parameters);row.addWidget(self.parameters)
        row.addWidget(self.actions['复制选中实例']);row.addWidget(self.actions['删除选中实例']);row.addStretch();box.addLayout(row);box.addStretch()
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.detail);scroll.setMaximumHeight(450);root.addWidget(scroll,1);root.addStretch()
        footer=QHBoxLayout();editor.message.setParent(self);editor.message.setObjectName('muted');footer.addWidget(editor.message,1)
        for name in ('保存设备配置','保存并加载场景'):footer.addWidget(self.actions[name])
        root.addLayout(footer)
        self.name.textEdited.connect(self.write_details);self.model.currentIndexChanged.connect(self.write_details)
        self.yaw.valueChanged.connect(self.write_details);self.target.currentIndexChanged.connect(self.write_details)
        for field in self.xyz:field.valueChanged.connect(self.write_details)
        # Structural edits already go through render; rebuild only the view.
        original=editor.render
        def render():original();self.refresh()
        editor.render=render
        for name in ('新增无人机','新增云台','复制选中实例','删除选中实例'):
            self.actions[name].clicked.connect(self.refresh)
        self.window.client.state_received.connect(self.update_status)
        self.window.client.connection_changed.connect(lambda *_:self.update_status(self.window.state))
        self.refresh()

    def refresh(self):
        selected=self.editor.table.currentRow();blocker=QSignalBlocker(self.table)
        self.table.setRowCount(len(self.editor.data['devices']))
        for row in range(self.table.rowCount()):self.update_row(row)
        del blocker
        drones=sum(x['kind']=='drone' for x in self.editor.data['devices'])
        self.summary.setText(f"初始配置 · {self.editor.scene['name']} · {drones} 架无人机 / {self.table.rowCount()-drones} 套云台")
        self.table.selectRow(max(0,min(selected,self.table.rowCount()-1)))
        self.select(self.table.currentRow())

    def update_row(self,row):
        source=self.editor.table;item=self.editor.data['devices'][row]
        model=source.cellWidget(row,2).currentText()
        values=[source.item(row,3).text()+'\n'+item['id'],model,'无人机' if item['kind']=='drone' else '光电云台',
                self.actual_status(item),' / '.join(f'{float(source.item(row,c).text()):.2f}' for c in (4,5,6)),'选择以编辑']
        for col,value in enumerate(values):self.table.setItem(row,col,QTableWidgetItem(value))

    def actual_status(self,item):
        if not self.window.client.ready:return '未连接'
        live=next((x for x in self.window.state.get('devices',[]) if x['id']==item['id']),None)
        if live is None:return '未加载'
        if item['kind']=='gimbal':return '已加载 · 模式见工作台'
        fleet=self.window.air_state.get('fleet') or [self.window.air_state]
        state=next((x for x in fleet if x.get('drone_id')==item['id']),{})
        return {'ready':'地面待命','active':'飞行中'}.get(state.get('flight_status'),'飞控状态未知')

    def update_status(self,*_):
        for row,item in enumerate(self.editor.data['devices']):
            cell=self.table.item(row,3)
            if cell:cell.setText(self.actual_status(item))

    def select(self,row):
        if row<0 or row>=len(self.editor.data['devices']):return
        self.loading=True;self.editor.table.selectRow(row)
        item=self.editor.data['devices'][row];table=self.editor.table
        self.identity.setText('设备详情 · '+item['id']);self.status.setText('初始配置草稿')
        self.name.setText(table.item(row,3).text());self.model.clear()
        for ident,template in MODELS.items():
            if template['kind']==item['kind']:self.model.addItem(template['name'],ident)
        self.model.setCurrentIndex(self.model.findData(table.cellWidget(row,2).currentData()))
        for col,field in enumerate(self.xyz,4):field.setValue(float(table.item(row,col).text()))
        self.yaw.setValue(float(table.item(row,7).text()));self.target.clear()
        target=table.cellWidget(row,8)
        for i in range(target.count()):self.target.addItem(target.itemText(i),target.itemData(i))
        self.target.setCurrentIndex(target.currentIndex());self.target.setEnabled(item['kind']=='gimbal');self.parameters.setEnabled(item['kind']=='gimbal')
        self.spec.setText('双光云台 · VIS 1920×1080 / IR 640×512 · 独立光心，安装参数在传感器页编辑。' if item['kind']=='gimbal' else '无人机外观型号独立；Mavic / Avata 当前共用四旋翼动力学。实际旋翼转速来自飞控。')
        self.loading=False

    def write_details(self,*_):
        if self.loading:return
        row=self.table.currentRow()
        if row<0:return
        table=self.editor.table
        source=self.sender()
        if source is self.name:table.item(row,3).setText(self.name.text())
        elif source is self.model:table.cellWidget(row,2).setCurrentIndex(table.cellWidget(row,2).findData(self.model.currentData()))
        elif source is self.yaw:table.item(row,7).setText(str(self.yaw.value()))
        elif source is self.target:table.cellWidget(row,8).setCurrentIndex(self.target.currentIndex())
        else:
            for col,field in enumerate(self.xyz,4):
                if source is field:table.item(row,col).setText(str(field.value()))
        blocker=QSignalBlocker(self.table);self.update_row(row);del blocker
        self.status.setText('有未保存编辑');self.editor.message.setText('本地设备草稿已修改；当前场景设备尚未改变。')

    def selected(self):
        row=self.table.currentRow()
        return self.editor.data['devices'][row] if row>=0 else None

    def place(self):
        item=self.selected()
        if not item:return
        tools=self.window.arrangement.tools
        index=next((i for i in range(tools.device.count()) if tools.device.itemData(i)[1]==item['id']),-1)
        if index<0:self.editor.message.setText('新增设备请先保存配置并加载场景，再进行放置。');return
        self.window.pages.setCurrentIndex(0);tools.device.setCurrentIndex(index)

    def open_parameters(self):
        item=self.selected()
        if not item or item['kind']!='gimbal':return
        if not any(x['id']==item['id'] for x in self.window.state.get('devices',[])):
            self.editor.message.setText('请先连接并加载此云台，再编辑其实际传感器参数。');return
        from apps.desktop_app.workbench_v3 import show_properties
        self.window.pages.setCurrentIndex(1);show_properties(self.window,'sensor',item['id']+'/visible')
