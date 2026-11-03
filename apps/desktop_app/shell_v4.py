"""V4 shell layered over existing command owners and stable page indices."""
from PySide6.QtCore import Qt, QSize, QSignalBlocker,QRect
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QButtonGroup, QPushButton, QLabel, QDockWidget, QMessageBox)
from apps.desktop_app.ui.icons import icon


class NavigationButton(QToolButton):
    """Every destination uses the same icon and label rectangles."""
    def __init__(self):
        super().__init__();self.setFixedSize(68,68)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#22344c' if self.isChecked() else '#1b2532' if self.underMouse() else '#15191f'))
        painter.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),6,6)
        if self.hasFocus():
            painter.setPen(QPen(QColor('#5797ff'),1));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),6,6)
        self.icon().paint(painter,QRect((self.width()-24)//2,10,24,24))
        painter.setPen(QColor('#c5ddff' if self.isChecked() else '#a2adbd'))
        painter.drawText(QRect(0,42,self.width(),20),Qt.AlignmentFlag.AlignCenter,self.text())


class DevicePage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.editor=None
        box=QVBoxLayout(self);box.setContentsMargins(12,12,12,12)
        row=QHBoxLayout();title=QLabel('设备管理');title.setObjectName('title');row.addWidget(title);row.addStretch()
        refresh=QPushButton('重新读取设备配置');refresh.clicked.connect(self.load);row.addWidget(refresh);box.addLayout(row)
        self.host=QVBoxLayout();box.addLayout(self.host,1)
        self.error=QLabel();self.error.setWordWrap(True);box.addWidget(self.error)
    def load(self):
        from apps.desktop_app.device_manager import DeviceManager
        if self.has_draft():
            answer=QMessageBox.question(self,'重新读取设备','存在未保存的设备草稿，重新读取将丢弃这些编辑。是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            if answer!=QMessageBox.StandardButton.Yes:return
        try:editor=DeviceManager(self.window)
        except (OSError,ValueError) as error:self.error.setText(str(error));return
        if self.editor:
            self.host.removeWidget(self.catalog_container);self.catalog_container.deleteLater();self.editor.deleteLater()
        self.editor=editor;editor.setWindowFlags(Qt.WindowType.Widget);editor.setParent(self)
        editor.accept=lambda:self.window.pages.setCurrentIndex(1)
        from apps.desktop_app.device_catalog import DeviceCatalog
        self.catalog=DeviceCatalog(editor);self.catalog_container=QWidget();row=QHBoxLayout(self.catalog_container);row.setContentsMargins(0,0,0,0)
        row.addWidget(self.catalog,1);row.addStretch();self.host.addWidget(self.catalog_container,1);self.error.clear()
    def has_draft(self):
        if self.editor is None:return False
        try:return self.editor.collect()!=self.editor.saved_snapshot
        except (OSError,ValueError):return True
    def showEvent(self,event):
        super().showEvent(event)
        if self.editor is None:self.load()


def install(w):
    root=w.centralWidget();outer=root.layout();outer.setContentsMargins(8,6,8,0);outer.setSpacing(6)
    for item in root.findChildren(QLabel):
        if item.objectName()=='brandMark':item.setFixedSize(34,36)
        if item.text()=='无人机 · 光电 · 多源仿真':item.hide()
    w.device_page=DevicePage(w);w.pages.addTab(w.device_page,'设备管理')
    # Keep arrangement=0/workbench=1/interfaces=2/settings=3 for existing routing.
    outer.removeWidget(w.pages);body=QHBoxLayout();body.setSpacing(8)
    w.navigation=QWidget();w.navigation.setObjectName('navigation');w.navigation.setFixedWidth(82)
    nav=QVBoxLayout(w.navigation);nav.setContentsMargins(4,12,4,8);nav.setSpacing(8)
    w.nav_group=QButtonGroup(w);w.nav_buttons={}
    for index,title,name in [(1,'工作台','screen'),(0,'场景编排','scene'),(4,'设备管理','devices'),(2,'数据接口','data'),(3,'资源设置','settings')]:
        button=NavigationButton();button.setObjectName('navButton');button.setText(title);button.setIcon(icon(name));button.setIconSize(QSize(24,24))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon);button.setCheckable(True);button.setMinimumHeight(62);button.setAccessibleName(title)
        w.nav_group.addButton(button,index);w.nav_buttons[index]=button;nav.addWidget(button,0,Qt.AlignmentFlag.AlignHCenter)
    nav.addStretch();w.nav_group.idClicked.connect(w.pages.setCurrentIndex)
    w.pages.tabBar().hide();w.pages.currentChanged.connect(lambda index:w.nav_buttons[index].setChecked(True) if index in w.nav_buttons else None)
    w.nav_buttons[w.pages.currentIndex()].setChecked(True);body.addWidget(w.navigation);body.addWidget(w.pages,1);outer.addLayout(body,1)
    w.input_mode.currentIndexChanged.connect(lambda _:update_context(w))
    w.client.state_received.connect(lambda _:update_context(w))
    update_context(w)
    w.workbench_split.setChildrenCollapsible(False);w.workbench_split.setSizes([210,1000,310])
    w.tree_panel.setMinimumWidth(180)
    # Move the original, correlated sensor editor intact into a dock.
    sensors=w.inspectors.widget(2);w.inspectors.removeTab(2)
    placeholder=QWidget();hint=QVBoxLayout(placeholder);hint.addWidget(QLabel('传感器参数在右侧编辑器中显示。'));hint.addStretch();w.inspectors.addTab(placeholder,'传感器')
    w.sensor_dock=QDockWidget('传感器参数',w);w.sensor_dock.setObjectName('v4SensorDock')
    w.sensor_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea);w.sensor_dock.setWidget(sensors);w.sensor_dock.setMinimumWidth(335)
    w.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,w.sensor_dock);w.sensor_dock.hide()
    power=w.sensor_settings.power_panel;w.gimbal_panel.layout().insertWidget(w.gimbal_panel.layout().count()-1,power)
    def open_sensor(*_):
        w.sensor_dock.setWindowTitle('传感器参数 · '+w.sensor_settings.device_id)
        w.sensor_dock.show();w.sensor_dock.raise_()
    w.open_sensor_editor=open_sensor
    def sensor_tab(index):
        if index==2:
            open_sensor()
            blocker=QSignalBlocker(w.inspectors);w.inspectors.setCurrentIndex(1);del blocker
    w.inspectors.currentChanged.connect(sensor_tab)
    w.inspectors.tabBar().hide()
    side=w.inspectors.parentWidget();side_layout=side.layout();row=QHBoxLayout()
    w.context_group=QButtonGroup(w)
    for index,title in [(0,'无人机'),(1,'云台')]:
        b=QPushButton(title);b.setCheckable(True);w.context_group.addButton(b,index);row.addWidget(b)
    edit=QPushButton('参数');edit.clicked.connect(open_sensor);row.addWidget(edit)
    side_layout.insertLayout(2,row);w.context_group.idClicked.connect(w.inspectors.setCurrentIndex)
    w.inspectors.currentChanged.connect(lambda index:w.context_group.button(index).setChecked(True) if w.context_group.button(index) else None)
    w.context_group.button(w.inspectors.currentIndex()).setChecked(True)
    w.rotors_button.hide()  # AirSim owns RPM; no animation-style primary control.
    w.gallery.note.setText('单击查看属性 · 明确接管后才控制 · 移除画面不停止采集')
    from apps.desktop_app.arrangement_v4 import install as arrange
    arrange(w.arrangement)
    from apps.desktop_app.workbench_polish import install as polish
    polish(w)


def update_context(w):
    """Show keyboard ownership without changing it during property selection."""
    if hasattr(w,'input_mode'):
        mode=w.input_mode.currentData()
        suffix=' · '+w.selected_drone if mode=='drone' else ' · '+w.selected_gimbal if mode=='gimbal' else ''
        w.input_mode.setToolTip('当前键盘：'+w.input_mode.currentText()+suffix+'；编辑字段时不接管驾驶')
