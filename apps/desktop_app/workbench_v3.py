"""Compact four-page shell. Presentation never silently takes control."""
from PySide6.QtCore import Qt, QSignalBlocker, QUrl, QSettings
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QComboBox, QLineEdit, QSpinBox, QPlainTextEdit, QTreeWidget,
    QSplitter, QPushButton, QFormLayout, QTableWidget, QHeaderView)
from core.config import ROOT
from apps.desktop_app.lidar_view import LidarView
from apps.desktop_app.ui.components import NumberInput, ChoiceInput, scroll


def build_workbench(w, config, image_type):
    root = QWidget(); root.setObjectName('appRoot'); w.setCentralWidget(root)
    outer = QVBoxLayout(root); outer.setContentsMargins(12,8,12,0); outer.setSpacing(8)
    header = QHBoxLayout(); header.setSpacing(12)
    mark=QLabel('W');mark.setObjectName('brandMark');mark.setFixedSize(42,42);mark.setAlignment(Qt.AlignmentFlag.AlignCenter);header.addWidget(mark)
    branding=QVBoxLayout();branding.setSpacing(0)
    branding.addWidget(w._label('WISEYE','brand'));branding.addWidget(w._label('SIMULATION STUDIO','brandSub'));header.addLayout(branding)
    header.addSpacing(14);header.addWidget(w._label('无人机 · 光电 · 多源仿真','muted'));header.addStretch()
    w.badge = w._label('未连接','badge'); header.addWidget(w.badge)
    from core.runtime_paths import IS_RELEASE
    w.quick_connect=w._button('启动仿真' if IS_RELEASE else '连接仿真', w.launch_ue if IS_RELEASE else w.connect_ue, True, False);header.addWidget(w.quick_connect)
    outer.addLayout(header)
    w.pages = QTabWidget(); w.pages.setObjectName('mainPages'); outer.addWidget(w.pages,1)
    run = QWidget(); run_layout=QVBoxLayout(run);run_layout.setContentsMargins(0,8,0,0);run_layout.setSpacing(8)
    modes=QHBoxLayout()
    w.active_scene=w._label('场景：未连接');modes.addWidget(w.active_scene)
    w.health_label=w._label('等待仿真推进');modes.addWidget(w.health_label,1)
    modes.addWidget(w._label('键盘输入'));w.input_mode=ChoiceInput()
    for label,mode in [('观察场景','observer'),('驾驶无人机','drone'),('操作云台','gimbal')]:w.input_mode.addItem(label,mode)
    w.input_mode.activated.connect(lambda _:change_input(w));w.control_widgets.append(w.input_mode);modes.addWidget(w.input_mode)
    w.performance_profile=ChoiceInput()
    for label,profile in [('画质 · 上限60 FPS','quality'),('均衡 · 上限45 FPS','balanced'),('节能 · 上限30 FPS','economy')]:w.performance_profile.addItem(label,profile)
    w.performance_profile.setCurrentIndex(1)
    w.performance_profile.setToolTip('UE 帧率上限不是实测。VIS/IR/OBS 捕获上限：画质30/25/15、均衡20/15/10、节能10/10/8 Hz；节能降低阴影与间接光。')
    w.performance_profile.activated.connect(lambda _:w.command('sim.set_performance_profile',{'profile':w.performance_profile.currentData()}))
    w.control_widgets.append(w.performance_profile);modes.addWidget(w.performance_profile);run_layout.addLayout(modes)
    from apps.desktop_app.runtime_panel import RuntimePanel
    w.runtime_panel=RuntimePanel(w);run_layout.addWidget(w.runtime_panel)
    w.workbench_split=QSplitter()
    tree=QWidget();tree.setObjectName('panel');tl=QVBoxLayout(tree);tl.setContentsMargins(10,10,10,10)
    tl.addWidget(w._label('设备与数据源','value'));w.object_search=QLineEdit();w.object_search.setPlaceholderText('搜索名称或 ID')
    w.object_search.textChanged.connect(lambda text:filter_tree(w,text));tl.addWidget(w.object_search)
    from apps.desktop_app.sensor_workspace import SourceTree
    w.object_tree=SourceTree();w.object_tree.setDragEnabled(True);w.object_tree.setHeaderHidden(True);tl.addWidget(w.object_tree,1)
    tl.addWidget(w._button('管理场景设备',lambda:w.fleet_selection.manage(),control=False));tree.setMinimumWidth(170)
    w.tree_panel=tree;w.workbench_split.addWidget(tree)
    from apps.desktop_app.sensor_workspace import SensorWorkspace
    w.gallery=SensorWorkspace(w,image_type);w.workbench_split.addWidget(w.gallery)
    w.pages.currentChanged.connect(lambda _:w.gallery.sync_clients() if hasattr(w,'host') else None)
    right=QWidget();right.setObjectName('panel');right.setMinimumWidth(290);right.setMaximumWidth(420)
    rl=QVBoxLayout(right);rl.setContentsMargins(12,12,12,12)
    w.inspector_title=w._label('无人机 · uav-01','value');w.inspector_title.setWordWrap(True);rl.addWidget(w.inspector_title)
    w.inspected_kind,w.inspected_id='drone','uav-01'
    w.inspector_takeover=w._button('设为控制对象',lambda:take_selected(w));rl.addWidget(w.inspector_takeover)
    from apps.desktop_app.device_manager import FleetSelection
    w.fleet_selection=FleetSelection(w);rl.addWidget(w.fleet_selection)
    w.inspectors=QTabWidget();w.inspectors.setObjectName('inspectors');rl.addWidget(w.inspectors,1);w.workbench_split.addWidget(right)
    w.workbench_split.setStretchFactor(1,1);w.workbench_split.setSizes([210,960,330]);run_layout.addWidget(w.workbench_split,1)

    drone=QWidget();drone.setObjectName('controlBody');dl=QVBoxLayout(drone);dl.setContentsMargins(0,10,0,0)
    w.drone_control_label=w._label('驾驶对象：uav-01','value');dl.addWidget(w.drone_control_label)
    w.flight_status_label=w._label('待连接');dl.addWidget(w.flight_status_label)
    actions=QHBoxLayout()
    for attr,label,command in [('takeoff_button','起飞','flight.takeoff'),('hover_button','悬停','flight.hover'),('land_button','降落','flight.land')]:
        button=w._button(label,lambda _=False,c=command:w.command(c),primary=attr=='takeoff_button')
        setattr(w,attr,button);w.flight_widgets.append(button);actions.addWidget(button)
    dl.addLayout(actions);dl.addWidget(w._label('FLIGHT PLAN  /  飞行任务','section'));w.flight=ChoiceInput()
    for label,mode in [('手动驾驶','manual'),('航线任务','auto')]:w.flight.addItem(label,mode)
    w.flight.activated.connect(w.set_flight_mode);dl.addWidget(w.flight);w.flight_widgets.append(w.flight);w.control_widgets.append(w.flight)
    w.manual_takeover=w._button('接管手动驾驶',lambda:take_manual(w))
    w.manual_takeover.setToolTip('先起飞，再明确接管键盘与按住移动按钮；接管会停止当前航线。')
    dl.addWidget(w.manual_takeover)
    from apps.desktop_app.route_editor import open_route_editor
    dl.addWidget(w._button('编辑航线 / 管理任务',lambda:open_route_editor(w),control=False))
    pause=QHBoxLayout()
    w.pause_button=w._button('暂停航线',lambda:w.command('sim.pause'))
    w.pause_button.setToolTip('暂停航线并悬停，不冻结物理时钟。')
    w.resume_button=w._button('继续航线',lambda:w.command('sim.resume'))
    w.reset_button=w._button('返回起点',lambda:confirm_route_reset(w))
    for b in (w.pause_button,w.resume_button,w.reset_button):pause.addWidget(b);w.flight_widgets.append(b)
    dl.addLayout(pause)
    dl.addWidget(w._label('MANUAL CONTROL  /  手动操控','section'))
    hint=w._label('按住按钮移动 · 松开停止')
    hint.setToolTip('W/S 前后 · A/D 左右 · R/F 升降 · Q/E 转向；仅在驾驶输入模式生效。');hint.setWordWrap(True);dl.addWidget(hint)
    grid=QGridLayout()
    for label,vec,row,col in [('上升',(0,0,1,0),0,0),('前进',(1,0,0,0),0,1),('下降',(0,0,-1,0),0,2),('向左',(0,-1,0,0),1,0),('悬停',(0,0,0,0),1,1),('向右',(0,1,0,0),1,2),('左转',(0,0,0,-1),2,0),('后退',(-1,0,0,0),2,1),('右转',(0,0,0,1),2,2)]:
        b=QPushButton(label);b.setObjectName('direction');b.setToolTip('按住移动，松开停止');b.pressed.connect(lambda v=vec:w.start_manual_input(v));b.released.connect(w.stop_manual_input)
        grid.addWidget(b,row,col);w.control_widgets.append(b);w.flight_widgets.append(b)
    dl.addLayout(grid)
    dl.addWidget(w._label('TELEMETRY  /  实时遥测','section'))
    w.position_label=w._label('位置：—','telemetry');w.position_label.setWordWrap(True);dl.addWidget(w.position_label)
    w.motor_label=w._label('电机 RPM：—','telemetry');w.motor_label.setWordWrap(True);dl.addWidget(w.motor_label)
    w.rotors_button=w._button('启动旋翼动画',lambda:w.command('rotors.set_enabled',{'enabled':not w.state.get('rotors_running',True)}));dl.addWidget(w.rotors_button)
    hint=w._label('型号和初始位置在场景编排中修改。');hint.setWordWrap(True);dl.addWidget(hint);dl.addStretch()
    w.drone_panel=drone;w.inspectors.addTab(scroll(drone),'无人机')

    gimbal=QWidget();gimbal.setObjectName('controlBody');gl=QVBoxLayout(gimbal);gl.setContentsMargins(0,10,0,0)
    gl.addWidget(w._label('真值跟踪目标'));w.tracking_target=ChoiceInput()
    w.tracking_target.activated.connect(lambda _:w.command('gimbal.set_target',{'drone_id':w.tracking_target.currentData()}))
    gl.addWidget(w.tracking_target);w.control_widgets.append(w.tracking_target)
    w.tracking_button=w._button('开始真值跟踪',lambda:w.command('gimbal.set_tracking',{'enabled':not w.state.get('tracking',True)}));gl.addWidget(w.tracking_button)
    gl.addWidget(w._button('接管手动云台',lambda:w.command('input.set_mode',{'mode':'gimbal'})))
    w.gimbal_hold_button=w._button('停止并保持方向',lambda:hold_gimbal(w))
    w.gimbal_hold_button.setToolTip('清除摇杆/键盘速度输入并退出真值跟踪，保持当前朝向。')
    gl.addWidget(w.gimbal_hold_button)
    from apps.desktop_app.gimbal_joystick import GimbalJoystick
    w.gimbal_stick=GimbalJoystick();w.gimbal_stick.moved.connect(w.set_gimbal_stick);gl.addWidget(w.gimbal_stick)
    w.angle_label=w._label('实际偏航 — / 俯仰 —');gl.addWidget(w.angle_label)
    form=QFormLayout();w.gimbal_yaw=NumberInput(-180,180,'°',1,.5);w.gimbal_pitch=NumberInput(-15,75,'°',1,.5)
    form.addRow('目标偏航',w.gimbal_yaw);form.addRow('目标俯仰',w.gimbal_pitch);gl.addLayout(form);w.control_widgets.extend([w.gimbal_yaw,w.gimbal_pitch])
    gl.addWidget(w._button('应用角度并保持',lambda:w.command('gimbal.set_angles',{'yaw_deg':w.gimbal_yaw.value(),'pitch_deg':w.gimbal_pitch.value()})))
    hint=w._label('摇杆/方向键需“操作云台”；松手或失焦停止。跟踪为 UE 真值指向。');hint.setWordWrap(True);gl.addWidget(hint);gl.addStretch()
    w.gimbal_panel=gimbal;w.inspectors.addTab(scroll(gimbal),'云台')
    from apps.desktop_app.sensor_forms import SensorSettings
    w.sensor_settings=SensorSettings(w);w.inspectors.addTab(w.sensor_settings,'传感器')
    w.sensor_settings.currentChanged.connect(lambda index:sensor_tab_changed(w,index))
    w.fov=w.sensor_settings.panels['visible']['fields']['fov_deg'];w.palette=w.sensor_settings.panels['infrared']['fields']['palette']
    w.lidar_parameters={k:v for k,v in w.sensor_settings.panels['lidar']['fields'].items() if k!='enabled'};w.lidar_dirty=set()
    w.sensor_applied=w._label('各传感器独立应用')
    w.object_tree.currentItemChanged.connect(lambda item,_:select_object(w,item))
    w.object_tree.itemDoubleClicked.connect(lambda item,_:add_tree_source(w,item))
    w.inspectors.currentChanged.connect(lambda index:select_inspector_tab(w,index))
    events=QHBoxLayout();w.log_toggle=QPushButton('事件与日志');w.log_toggle.setObjectName('ghost');events.addWidget(w.log_toggle)
    w.event_preview=w._label('等待连接仿真')
    from PySide6.QtWidgets import QSizePolicy
    w.event_preview.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);events.addWidget(w.event_preview,1)
    for label,panel in [('设备栏',tree),('操作栏',right)]:
        b=QPushButton(label);b.setObjectName('ghost');b.clicked.connect(lambda _,p=panel:p.setVisible(not p.isVisible()));events.addWidget(b)
    run_layout.addLayout(events)
    w.logs=QPlainTextEdit();w.logs.setReadOnly(True);w.logs.setMaximumBlockCount(500);w.logs.setMaximumHeight(130);w.logs.hide()
    w.log_toggle.clicked.connect(lambda:w.logs.setVisible(not w.logs.isVisible()));run_layout.addWidget(w.logs)
    from apps.desktop_app.arrangement import ArrangementPage
    w.arrangement=ArrangementPage(w);w.pages.addTab(w.arrangement,'场景编排');w.pages.addTab(run,'仿真工作台')
    from apps.desktop_app.secondary_pages import build_secondary_pages
    build_secondary_pages(w,config,copy_sources)
    w.latency=QLabel('控制响应 —');w.statusBar().addPermanentWidget(w.latency)
    # Unmounted compatibility sinks used by old command/diagnostic handlers.
    w.summary_values={key:(QLabel(),QLabel()) for key in ('simulation','gimbal','sensor')}
    w.video_channel=QComboBox()
    for label,key in [('可见光','CH1'),('红外','CH2'),('点云','LIDAR'),('双模态','BOTH'),('全部','ALL')]:w.video_channel.addItem(label,key)
    w.video_channel.setCurrentIndex(4);w.view_tabs=QTabWidget()
    w.image,w.dual_visible,w.dual_infrared=image_type(),image_type(),image_type();w.lidar=LidarView()
    w.dual_ir_caption,w.image_caption,w.input_hint=QLabel(),QLabel(),QLabel();w.capture_button=QPushButton()
    w.drone_model=QComboBox();w.drone_model.addItem('Mavic 3','mavic3');w.drone_model.addItem('Avata','avata')
    w.observer_mode=ChoiceInput()
    for label,mode in [('全景','overview'),('自由观察','free'),('云台视角','gimbal'),('无人机跟随','follow')]:w.observer_mode.addItem(label,mode)
    w.gallery.layout().itemAt(0).layout().insertWidget(2,w.observer_mode)
    w.observer_mode.activated.connect(lambda _:w.command('observer.set_mode',{'mode':w.observer_mode.currentData()}));w.control_widgets.append(w.observer_mode)
    for widget in (w.image,w.dual_visible,w.dual_infrared,w.lidar,w.sensor_applied):widget.setParent(root);widget.hide()
    state=QSettings('WISEYE','Studio').value('workbench/split')
    if state:w.workbench_split.restoreState(state)
    from apps.desktop_app.ui.icons import decorate
    decorate(w)
    refresh_inspector(w)


def change_input(w):
    w.clear_gimbal_input();w.manual_keys.clear();w.stop_manual_input()
    w.command('input.set_mode',{'mode':w.input_mode.currentData()});w.update_flight_controls()


def take_manual(w):
    w.flight.setCurrentIndex(w.flight.findData('manual'))
    w.set_flight_mode()


def show_properties(w,kind,ident):
    w.inspected_kind,w.inspected_id=kind,ident
    if kind=='sensor':
        device,sensor=ident.split('/',1);w.sensor_settings.select_device(device)
        w.sensor_settings.setCurrentIndex({'visible':0,'infrared':1,'lidar':2}[sensor])
    blocker=QSignalBlocker(w.inspectors)
    w.inspectors.setCurrentIndex({'drone':0,'gimbal':1,'sensor':2}[kind]);del blocker;refresh_inspector(w)


def select_inspector_tab(w,index):
    kind=('drone','gimbal','sensor')[index]
    if kind=='sensor':
        device=w.inspected_id.split('/')[0] if w.inspected_kind in ('gimbal','sensor') else w.selected_gimbal
        sensor=('visible','infrared','lidar')[w.sensor_settings.currentIndex()]
        w.sensor_settings.select_device(device);w.inspected_id=device+'/'+sensor
    else:w.inspected_id=w.selected_drone if kind=='drone' else w.selected_gimbal
    w.inspected_kind=kind;refresh_inspector(w)


def sensor_tab_changed(w,index):
    if w.inspectors.currentIndex()==2:
        w.inspected_kind='sensor'
        w.inspected_id=w.sensor_settings.device_id+'/'+('visible','infrared','lidar')[index]
        refresh_inspector(w)


def refresh_inspector(w):
    if not hasattr(w,'inspected_id'):return
    kind,ident=w.inspected_kind,w.inspected_id
    w.inspector_title.setText({'drone':'无人机','gimbal':'光电云台','sensor':'传感器'}[kind]+' · '+ident)
    mismatch=(kind=='drone' and ident!=w.selected_drone) or (kind=='gimbal' and ident!=w.selected_gimbal)
    w.inspector_takeover.setVisible(mismatch);w.inspector_takeover.setText('设为驾驶对象' if kind=='drone' else '设为云台控制对象')
    w.drone_panel.setVisible(not(kind=='drone' and mismatch));w.gimbal_panel.setVisible(not(kind=='gimbal' and mismatch))


def take_selected(w):
    if w.inspected_kind in ('drone','gimbal'):w.fleet_selection.select(w.inspected_kind,w.inspected_id);refresh_inspector(w)


def select_object(w,item):
    value=item.data(0,Qt.ItemDataRole.UserRole) if item else None
    if value:show_properties(w,*value)


def add_tree_source(w,item):
    value=item.data(0,Qt.ItemDataRole.UserRole) if item else None
    if value and value[0]=='sensor':w.gallery.add_source(value[1])


def filter_tree(w,text):
    text=text.casefold().strip()
    def visit(node):
        found=text in node.text(0).casefold() or text in node.toolTip(0).casefold()
        for i in range(node.childCount()):found=visit(node.child(i)) or found
        node.setHidden(not found);return found
    for i in range(w.object_tree.topLevelItemCount()):visit(w.object_tree.topLevelItem(i))


def confirm_route_reset(w):
    from PySide6.QtWidgets import QMessageBox
    if QMessageBox.question(w,'返回航线起点',f'让 {w.selected_drone} 返回航线起点？此操作会改变飞行位置。')==QMessageBox.StandardButton.Yes:w.command('sim.reset')


def copy_sources(w):
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setText(w.source_urls.toPlainText())


def update_sources(w):
    """Refresh all discovered sources without resetting table selection every poll."""
    from PySide6.QtWidgets import QApplication, QTableWidgetItem, QMenu
    from apps.desktop_app.source_registry import SIZES
    registry=w.gallery.registry
    keys=[key for key,source in registry.items() if source.device_id not in w.gallery.missing]
    signature=tuple(keys)
    if getattr(w,'source_signature',None)!=signature:
        w.source_signature=signature;w.source_table.setRowCount(len(keys))
        for row,key in enumerate(keys):
            source=registry[key]
            w.source_table.setItem(row,0,QTableWidgetItem(source.title))
            size=SIZES.get(source.sensor_id)
            w.source_table.setItem(row,1,QTableWidgetItem('×'.join(map(str,size)) if size else '48×12 · 米制'))
            w.source_table.setItem(row,2,QTableWidgetItem('待确认'))
            w.source_table.setItem(row,3,QTableWidgetItem(''))
            button=QPushButton('操作');menu=QMenu(button);button.setMenu(menu)
            from apps.desktop_app.interface_settings import edit_interfaces
            menu.addAction('编辑接口',lambda k=key:edit_interfaces(w,registry[k]))
            menu.addAction('复制接口',lambda k=key:QApplication.clipboard().setText(registry[k].url(w.host.text().strip(),w.config) or f'JSON Lines {w.host.text().strip()}:{w.port.value()} · sensor.lidar.get_points · device_id={registry[k].device_id}'))
            menu.addAction('添加到工作区',lambda k=key:w.gallery.add_source(k))
            if source.sensor_id!='observer':menu.addAction('保存原始单帧',lambda k=key:w.capture_source(registry[k].device_id,registry[k].sensor_id))
            w.source_table.setCellWidget(row,4,button)
    for row,key in enumerate(keys):
        source=registry[key];state=w.gallery.states.get(source.device_id,{})
        actual=state.get('sensors',{}).get(source.sensor_id,{})
        text=('仿真未连接' if not w.client.ready else '观察输出' if source.sensor_id=='observer' else '采集中' if actual.get('enabled') else '已停用' if actual else '未读取状态')
        w.source_table.item(row,2).setText(text)
        w.source_table.item(row,3).setText(source.url(w.host.text().strip(),w.config) or f'JSON Lines · {w.port.value()} · {source.device_id}')
    clients=w.gallery.clients
    pending=sum(client.statistics()['pending'] for client in clients.values())
    dropped=sum(client.statistics()['overwritten'] for client in clients.values())
    fresh=' / '.join(k+': '+f'{fps:.1f} Hz' for k,fps in w.gallery.fps.items() if k in w.gallery.sources)
    w.performance.setText(f"性能档位：{w.state.get('performance_profile','—')} · 预览订阅 {len(clients)} · 待显示 {pending} 帧（每源至多1帧） · 累计覆盖旧帧 {dropped}\n已测新帧：{fresh or '等待统计'}\n新帧率来自 UE 完成帧计数；画面接收时间不等于采集时间。延迟实测见使用说明。")


def hold_gimbal(w):
    w.clear_gimbal_input()
    w.command('gimbal.set_tracking',{'enabled':False})
