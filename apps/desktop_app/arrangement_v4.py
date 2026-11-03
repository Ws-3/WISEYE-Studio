"""Scene-first arrangement using the workspace's one shared observer source."""
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSplitter, QListWidget, QScrollArea, QFormLayout)


def install(page):
    w=page.window;page._v4_layout=True
    # Detach the old presentation; commands and field owners remain unchanged.
    outer=page.layout()
    while outer.count():
        item=outer.takeAt(0)
        if item.widget():item.widget().hide()
    outer.setContentsMargins(8,8,8,6);outer.setSpacing(8)
    heading=QHBoxLayout();title=QLabel('场景编排');title.setObjectName('title');heading.addWidget(title)
    heading.addWidget(w.scenes,1);manage=QPushButton('管理设备');manage.clicked.connect(lambda:w.pages.setCurrentIndex(4));heading.addWidget(manage)
    save=QPushButton('保存初始布置');save.clicked.connect(page.save);heading.addWidget(save);outer.addLayout(heading)
    split=QSplitter();split.setChildrenCollapsible(False);outer.addWidget(split,1);page.v4_split=split
    left=QWidget();left.setObjectName('panel');ll=QVBoxLayout(left);ll.setContentsMargins(12,12,12,12)
    ll.addWidget(w._label('场景设备','value'));page.v4_device_list=QListWidget();ll.addWidget(page.v4_device_list,1)
    ll.addWidget(w._label('布置预设','section'));ll.addWidget(page.tools.presets);page.tools.presets.setMinimumWidth(0)
    ll.addWidget(page.tools.name);new=QPushButton('另存为新预设');new.clicked.connect(lambda:page.tools.save_named(False));ll.addWidget(new);ll.addWidget(page.tools.update_button)
    split.addWidget(left)
    center=QWidget();cl=QVBoxLayout(center);cl.setContentsMargins(0,0,0,0);cl.setSpacing(6)
    bar=QHBoxLayout();bar.addWidget(w._label('UE · 场景观察 / 放置预览','value'));bar.addStretch()
    free=QPushButton('接管自由观察');free.clicked.connect(w.gallery.activate_observer);bar.addWidget(free);cl.addLayout(bar)
    page.scene_view=w.gallery.observer_type();page.scene_view.setMinimumSize(260,220);cl.addWidget(page.scene_view,1)
    info=w._label('到UE放置完整模型 · WASD移动 / QE转向 / RF升降 · Shift精调','hint');info.setWordWrap(True);cl.addWidget(info)
    split.addWidget(center)
    right=QWidget();right.setObjectName('panel');rl=QVBoxLayout(right);rl.setContentsMargins(12,12,12,12);rl.setSpacing(10)
    page.v4_position_title=w._label('设备位置与姿态','value');rl.addWidget(page.v4_position_title)
    fields=QWidget();page.position_grid=QGridLayout(fields);page.position_grid.setContentsMargins(0,0,0,0);rl.addWidget(fields)
    form=QFormLayout();form.addRow('距表面高度',page.tools.clearance);rl.addLayout(form)
    for button in (page.tools.pick,page.tools.snap,page.tools.cancel):rl.addWidget(button)
    rl.addWidget(page.tools.live);apply=QPushButton('应用所选设备位置');apply.setObjectName('primary');apply.clicked.connect(page.tools.apply_selected);rl.addWidget(apply)
    note=w._label('确认或编辑后实时应用。保存保留下次位置；新增、删除或换地图仍需加载。无人机须落地待命。','hint');note.setWordWrap(True);rl.addWidget(note);rl.addStretch()
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(right);scroll.setMinimumWidth(300);scroll.setMaximumWidth(400);split.addWidget(scroll)
    split.setStretchFactor(1,1);split.setSizes([210,1000,320])
    footer=QHBoxLayout();page.message.setObjectName('muted');footer.addWidget(page.message,1)
    reload=QPushButton('重新读取');reload.clicked.connect(page.load);footer.addWidget(reload);footer.addWidget(w.switch_button);outer.addLayout(footer)
    # Unmounted selection remains the sole identity owner used by placement RPCs.
    page.tools.device.setParent(page);page.tools.device.hide()
    page.v4_device_list.currentRowChanged.connect(lambda index:page.tools.device.setCurrentIndex(index) if index>=0 else None)
    page.tools.device.currentIndexChanged.connect(lambda _:select_device(page))
    page.sync_devices(page.device_specs)


def refresh_devices(page):
    selected=page.tools.device.currentIndex();blocker=QSignalBlocker(page.v4_device_list);page.v4_device_list.clear()
    for device in page.device_specs:
        kind='无人机' if device['kind']=='drone' else '光电云台'
        page.v4_device_list.addItem(kind+' · '+device['id']+'\n'+device.get('name',device['id']))
    page.v4_device_list.setCurrentRow(selected);del blocker
    select_device(page)


def select_device(page):
    current=page.tools.device.currentData();key=current[1] if current else None
    for ident,widgets in getattr(page,'v4_field_groups',{}).items():
        for widget in widgets:widget.setVisible(ident==key)
    if current:
        page.v4_position_title.setText(current[0]+' · 世界坐标 / 米')
        blocker=QSignalBlocker(page.v4_device_list);page.v4_device_list.setCurrentRow(page.tools.device.currentIndex());del blocker
