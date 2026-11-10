"""Bring the existing controls into the approved compact workspace hierarchy."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QToolButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QDialog, QFrame,QMenu)
from core.runtime_metrics import number


class AdvancedControl(QWidget):
    def __init__(self,body,title):
        super().__init__();self.body=body;self.title=title
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0)
        self.toggle=QPushButton(title+'…');self.toggle.setObjectName('ghost');box.addWidget(self.toggle)
        self.dialog=QDialog(self);self.dialog.setWindowTitle('WISEYE · '+title);self.dialog.resize(400,230)
        content=QVBoxLayout(self.dialog);content.addWidget(self.body)
        self.toggle.clicked.connect(self.open);self.dialog.finished.connect(self.stop_inputs)

    def open(self):self.dialog.show();self.dialog.raise_()

    def stop_inputs(self,*_):
        owner=self.window()
        if hasattr(owner,'clear_gimbal_input'):owner.clear_gimbal_input();owner.manual_keys.clear();owner.stop_manual_input()


def advanced_control(widget,title):return AdvancedControl(widget,title)


class MachineSummary(QFrame):
    def __init__(self,w):
        super().__init__();self.w=w;self.setObjectName('machineSummary')
        box=QVBoxLayout(self);box.setContentsMargins(4,10,4,0);box.setSpacing(6)
        title=QLabel('仿真运行主机');title.setObjectName('section');box.addWidget(title)
        self.gpu=QLabel('GPU · 未连接');self.gpu.setWordWrap(True);box.addWidget(self.gpu)
        self.rating=QLabel('运行评估 · 未评估');box.addWidget(self.rating)
        self.fps=QLabel('UE 推进 · —');box.addWidget(self.fps)
        self.vram=QLabel('显存 · —');box.addWidget(self.vram)
        self.warning=QLabel();self.warning.setWordWrap(True);self.warning.setObjectName('warningText');box.addWidget(self.warning)
        button=QPushButton('运行诊断');button.setObjectName('ghost');button.clicked.connect(self.open);box.addWidget(button)
        self.dialog=QDialog(w);self.dialog.setWindowTitle('WISEYE · 运行诊断');self.dialog.resize(760,270)
        panel=QVBoxLayout(self.dialog);panel.addWidget(w.health_label);w.health_label.show();panel.addWidget(w.runtime_panel)
        w.client.state_received.connect(self.update_state)
        w.client.connection_changed.connect(lambda ready,_:None if ready else self.clear())
        w.runtime_panel.rating_changed.connect(self.update_rating)

    def update_rating(self,grade,reason,color):
        self.rating.setText('运行评估 · '+grade);self.rating.setToolTip(reason);self.rating.setStyleSheet('color:'+color+';')

    def clear(self):
        self.gpu.setText('GPU · 未连接');self.rating.setText('运行评估 · 未评估');self.fps.setText('UE 推进 · —');self.vram.setText('显存 · —');self.warning.clear()

    def update_state(self,state):
        data=state.get('runtime_hardware',{})
        if not data:self.clear();return
        self.gpu.setText(data.get('gpu_name','GPU · 未提供'))
        fps=number(data,'ue_fps');used=number(data,'ue_vram_used_bytes');budget=number(data,'ue_vram_budget_bytes')
        self.fps.setText('UE 推进 · '+('不可用' if fps is None else f'{fps:.1f} FPS'))
        self.vram.setText('显存 · '+('不可用' if used is None or budget is None else f'{used/1024**3:.2f} / {budget/1024**3:.2f} GiB'))
        self.vram.setToolTip('UE 进程使用 / 驱动预算；预算不是显卡物理容量。')
        self.warning.setText(self.w.runtime_panel.warning.text())
        rating=self.w.runtime_panel.rating
        self.rating.setText(rating.text());self.rating.setStyleSheet(rating.styleSheet());self.rating.setToolTip(rating.toolTip())

    def open(self):self.dialog.show();self.dialog.raise_()


def install(w):
    run=w.pages.widget(1);layout=run.layout()
    layout.removeWidget(w.runtime_panel)
    w.machine_summary=MachineSummary(w);w.tree_panel.layout().addWidget(w.machine_summary)
    # Put global scene actions in the existing viewport toolbar, rather than
    # allocating another row for connection, diagnostics and profile controls.
    w.scene_tools=QToolButton();w.scene_tools.setText('场景');w.scene_tools.setToolTip('环境与天气、性能与画质')
    w.scene_tools.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    w.scene_tools_menu=QMenu(w.scene_tools)
    w.environment_action=w.scene_tools_menu.addAction('环境与天气…');w.environment_action.triggered.connect(w.runtime_panel.open_environment)
    from apps.desktop_app.observation_panel import open_aerial,open_population
    w.aerial_action=w.scene_tools_menu.addAction('无人机航拍…');w.aerial_action.triggered.connect(lambda:open_aerial(w))
    w.population_action=w.scene_tools_menu.addAction('车辆与行人…');w.population_action.triggered.connect(lambda:open_population(w))
    quality=w.scene_tools_menu.addAction('性能与画质…')
    quality.triggered.connect(lambda:(w.pages.setCurrentIndex(3),w.settings_navigation.setCurrentRow(1)))
    w.scene_tools.setMenu(w.scene_tools_menu);w.gallery.layout().itemAt(0).layout().insertWidget(3,w.scene_tools)
    # Reuse the sole keyboard selector in the existing ownership strip.
    w.ownership=QLabel();w.ownership.setObjectName('ownershipBar');w.ownership.setWordWrap(True)
    ownership=QWidget();row=QHBoxLayout(ownership);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
    row.addWidget(w.ownership,1);row.addWidget(QLabel('键盘'));row.addWidget(w.input_mode);w.input_mode.setMaximumWidth(130)
    right=w.inspectors.parentWidget();rl=right.layout()
    row.setDirection(QHBoxLayout.Direction.TopToBottom)
    w.ownership.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    rl.insertWidget(0,ownership)
    w.flight_status_label.setParent(right)
    safety=QWidget();safety.setObjectName('controlBody');safe=QVBoxLayout(safety);safe.setContentsMargins(0,2,0,4);safe.setSpacing(6)
    safe.addWidget(w.flight_status_label);actions=QHBoxLayout()
    for button in (w.takeoff_button,w.hover_button,w.land_button):actions.addWidget(button)
    safe.addLayout(actions);rl.insertWidget(rl.indexOf(w.inspectors),safety)
    w.drone_safety=safety
    w.inspectors.currentChanged.connect(lambda index:safety.setVisible(index in (0,3)));safety.setVisible(w.inspectors.currentIndex()==0)
    w.drone_control_label.hide()
    w.gimbal_stick.setMaximumHeight(150)
    from apps.desktop_app.gimbal_device import open_device
    device=QPushButton('设备数值与坐标…');device.clicked.connect(lambda:open_device(w))
    w.gimbal_panel.layout().insertWidget(0,device)
    # Device selectors remain above the contextual view. Avoid duplicate titles.
    w.gallery.note.setText('滚轮缩放 · 双击复位 · 拖动标题换位 · 参数从右侧或菜单打开')
    update(w)
    w.client.state_received.connect(lambda _:update(w));w.air_client.state_received.connect(lambda _:update(w))
    w.client.connection_changed.connect(lambda *_:update(w));w.input_mode.currentIndexChanged.connect(lambda _:update(w))
    from apps.desktop_app.mission_workspace import MissionWorkspace
    w.mission_workspace=MissionWorkspace(w)


def update(w):
    w.ownership.setText(f'驾驶：{w.selected_drone}    云台控制：{w.selected_gimbal}')
    w.ownership.setToolTip('使用接管按钮改变键盘归属。点击预览不会打开参数；输入框内编辑不会驾驶。')
    if hasattr(w,'drone_safety'):w.drone_safety.setVisible(w.inspectors.currentIndex() in (0,3))
