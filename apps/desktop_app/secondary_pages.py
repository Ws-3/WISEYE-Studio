"""Data integration and resource pages using the shared studio visual system."""
from PySide6.QtCore import QUrl,QSignalBlocker
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QSpinBox,QTableWidget,QHeaderView,QPlainTextEdit,QComboBox
from core.config import ROOT
from apps.desktop_app.ui.components import scroll


def card(w,title,subtitle):
    box=QFrame();box.setObjectName('arrangeCard');layout=QVBoxLayout(box);layout.setContentsMargins(18,14,18,16);layout.setSpacing(10)
    layout.addWidget(w._label(title,'value'))
    hint=w._label(subtitle);hint.setWordWrap(True);layout.addWidget(hint)
    return box,layout


def document(path):
    from core.runtime_paths import RESOURCE_ROOT
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(RESOURCE_ROOT/path)))


def data_directory(path=''):
    from core.runtime_paths import DATA_ROOT
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_ROOT/path)))


def build_secondary_pages(w,config,copy_sources):
    data=QWidget();d=QVBoxLayout(data);d.setContentsMargins(0,14,0,0);d.setSpacing(12)
    d.addWidget(w._label('连接数据，扩展能力','title'))
    d.addWidget(w._label('按设备订阅原始输出，将感知与处理交给扩展应用。'))
    streams,sl=card(w,'数据源目录','视频通过 RTSP 输出；点云通过 JSON Lines 查询。关闭本地画面不会关闭外部输出。')
    w.source_table=QTableWidget(0,5);w.source_table.setHorizontalHeaderLabels(['设备 / 数据源','规格','采集状态','接口地址','操作'])
    w.source_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);w.source_table.setAlternatingRowColors(True);w.source_table.setShowGrid(False)
    w.source_table.verticalHeader().hide();w.source_table.verticalHeader().setDefaultSectionSize(44)
    header=w.source_table.horizontalHeader();header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);header.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
    sl.addWidget(w.source_table,1);d.addWidget(streams,1)
    from apps.desktop_app.interface_settings import edit_interfaces
    sl.addWidget(w._button('编辑网络与传感器接口',lambda:edit_interfaces(w),control=False))
    details=QWidget();dl=QVBoxLayout(details);dl.setContentsMargins(0,0,0,0);dl.setSpacing(12)
    paired,pl=card(w,'同组图像与 GT','训练端独立连接数据通道；可见光与红外保留同组身份和各自原始标注。')
    gt_address=w._label('','telemetry');gt_address.setWordWrap(True);pl.addWidget(gt_address)
    gt_status=w._label('数据通道未探测；请在训练端确认连接，UE 已连接不代表数据服务可用。','hint');gt_status.setWordWrap(True);pl.addWidget(gt_status)
    actions=QHBoxLayout()
    from apps.desktop_app.training_launcher import launch_training
    actions.addWidget(w._button('打开训练端连接',lambda:launch_training(w),control=False))
    actions.addWidget(w._button('同组数据接口说明',lambda:document('docs/TRAINING_DATA_INTERFACE.md'),control=False));actions.addStretch();pl.addLayout(actions);dl.addWidget(paired)
    control,cl=card(w,'云台控制 API','已提供仿真云台角度、比例速度、目标跟踪、停止输入与保持方向接口；按 device_id 区分实例。')
    text=w._label('TCP / JSON Lines · 能力查询 · 状态回读 · 300 ms 速度输入超时保护','section');text.setWordWrap(True);cl.addWidget(text)
    row=QHBoxLayout()
    for title,path in [('接口文档','docs/GIMBAL_INTERFACE.md'),('Python SDK','integrations/gimbal_client.py'),('接入示例','examples/gimbal_control.py')]:row.addWidget(w._button(title,lambda _,p=path:document(p),control=False))
    row.addStretch();cl.addLayout(row)
    hint=w._label('目前连接仿真云台；实体硬件驱动、鉴权和多客户端控制仲裁尚未实现。','hint');hint.setWordWrap(True);cl.addWidget(hint);dl.addWidget(control)
    flight,fl=card(w,'无人机飞控 API','与数据通道分离；起降、手动输入与航线均由当前飞控服务执行。')
    flight_address=w._label('','telemetry');flight_address.setWordWrap(True);fl.addWidget(flight_address)
    fl.addWidget(w._button('飞控协议与命令说明',lambda:document('docs/PROTOCOL.md'),control=False));dl.addWidget(flight)
    def update_endpoints(*_):
        gt_address.setText(f'默认 TCP / JSON Lines · {w.config.host}:50100 · 在训练端可编辑连接目标')
        flight_address.setText(f"TCP / JSON Lines · {w.config.host}:{w.config.airsim_port} · "+('飞控已连接' if w.air_client.ready else '未连接'))
    w.client.connection_changed.connect(update_endpoints);w.air_client.connection_changed.connect(update_endpoints);w.client.state_received.connect(update_endpoints);update_endpoints()
    output,ol=card(w,'订阅信息与运行统计','接口地址对应当前控制云台；所有数据源可在上表逐项复制。')
    w.source_urls=QPlainTextEdit();w.source_urls.setReadOnly(True);w.source_urls.setMaximumHeight(90);ol.addWidget(w.source_urls)
    w.performance=w._label('等待仿真统计；端到端延迟未测量。');w.performance.setWordWrap(True);ol.addWidget(w.performance)
    ol.addWidget(w._button('复制当前云台订阅信息',lambda:copy_sources(w),control=False));dl.addWidget(output)
    area=scroll(details);area.setMinimumHeight(180);area.setMaximumHeight(380);d.addWidget(area)
    w.pages.addTab(data,'数据与接口')

    settings=QWidget();s=QVBoxLayout(settings);s.setContentsMargins(0,14,8,12);s.setSpacing(14)
    s.addWidget(w._label('工作环境与资源','title'));s.addWidget(w._label('管理仿真连接、场景资源与本机工作区。'))
    connection,c=card(w,'01  /  仿真连接','桌面控制服务与飞控服务的连接状态分别显示。')
    form=QFormLayout();w.host,w.port=QLineEdit(config.host),QSpinBox();w.port.setRange(1024,65535);w.port.setValue(config.port)
    form.addRow('UE 地址',w.host);form.addRow('控制端口',w.port);c.addLayout(form)
    c.addWidget(w._button('编辑并保存连接 / RTSP 参数',lambda:edit_interfaces(w),control=False))
    w.connect_button=w._button('连接 UE',w.connect_ue,True,False);w.disconnect_button=w._button('断开连接',w.disconnect_ue,control=False)
    w.connect_button.hide();w.disconnect_button.hide()
    c.addWidget(QLabel('使用右上角连接状态按钮连接／断开，启动按钮启动／关闭本次仿真。'))
    w.connection_detail,w.air_connection_detail=w._label('UE · 未连接','telemetry'),w._label('飞控 · 未连接','telemetry')
    for label in (w.connection_detail,w.air_connection_detail):label.setWordWrap(True);c.addWidget(label)
    s.addWidget(connection)
    resources,r=card(w,'02  /  场景与输出','管理地图资源，查看按设备保存的原始数据。')
    row=QHBoxLayout();row.addWidget(w._button('地图管理 / 导入',w.manage_scenes,control=False));row.addWidget(w._button('打开运行输出',lambda:data_directory('ue5/WISEYE/Saved/WISEYE'),control=False));row.addStretch();r.addLayout(row)
    from core.scenes import SceneStore
    scenes,_=SceneStore(ROOT).list();city=next((x for x in scenes if x['id']=='city'),{})
    city_status='已接入 · Small City' if city.get('installed') else '接入中，尚未就绪' if city.get('source_map') else '待接入'
    r.addWidget(w._label('City Sample  ·  '+city_status,'section'));s.addWidget(resources)
    workspace,l=card(w,'03  /  本机工作区','窗口布局保存在本机；场景设备配置通过 Git 同步。')
    from apps.desktop_app.language import language_selector
    language_form=QFormLayout();language_form.addRow('界面语言',language_selector(w))
    l.addLayout(language_form)
    l.addWidget(w._label('界面语言即时生效，并在下次启动时保留。'))
    l.addWidget(w._button('恢复默认场景主导画面布局',w.gallery.reset_layout,control=False))
    l.addWidget(w._button('查看运行说明',lambda:document('docs/DESKTOP.md'),control=False));s.addWidget(workspace);s.addStretch()
    quality,q=card(w,'性能与画质','修改当前仿真的质量档位；显示上限不等于实际帧率。')
    profile=QComboBox()
    for i in range(w.performance_profile.count()):profile.addItem(w.performance_profile.itemText(i),w.performance_profile.itemData(i))
    profile.setCurrentIndex(w.performance_profile.currentIndex());profile.setEnabled(False)
    profile.activated.connect(lambda _:w.command('sim.set_performance_profile',{'profile':profile.currentData()}))
    q.addWidget(profile)
    def sync_quality(*_):
        blocker=QSignalBlocker(profile);profile.setCurrentIndex(profile.findData(w.performance_profile.currentData()));del blocker
        profile.setEnabled(w.client.ready)
    w.client.state_received.connect(sync_quality);w.client.connection_changed.connect(sync_quality)
    w.performance_profile.currentIndexChanged.connect(sync_quality)
    explanation=w._label('不同档位改变 UE 推进上限、捕获频率与阴影／间接光质量。详细硬件使用和低性能建议可在运行诊断查看。','hint');explanation.setWordWrap(True);q.addWidget(explanation)
    q.addWidget(w._button('查看运行诊断',lambda:w.machine_summary.open(),control=False))
    storage,st=card(w,'存储工作区','仿真输出与日志使用当前会话数据目录；训练样本目录在训练端独立设置。')
    from core.runtime_paths import DATA_ROOT,IS_RELEASE
    directory=QLineEdit(str(DATA_ROOT));directory.setReadOnly(True);st.addWidget(directory)
    row=QHBoxLayout();row.addWidget(w._button('打开数据目录',lambda:data_directory(),control=False));row.addWidget(w._button('打开运行日志',lambda:data_directory('logs'),control=False));row.addStretch();st.addLayout(row)
    r.addWidget(w._label('运行方式 · '+('独立运行包' if IS_RELEASE else '源码开发版'),'muted'))
    # Reuse the existing connected controls in a short section navigation.
    from PySide6.QtWidgets import QListWidget,QStackedWidget
    for item in (connection,resources,workspace):s.removeWidget(item)
    sections=QWidget();shell=QHBoxLayout(sections);shell.setContentsMargins(8,10,8,8)
    navigation=QListWidget();navigation.addItems(['连接与会话','性能与画质','存储工作区','窗口与语言','场景与版本']);navigation.setFixedWidth(170)
    stack=QStackedWidget()
    for item in (connection,quality,storage,workspace,resources):
        page=QWidget();box=QVBoxLayout(page);box.setContentsMargins(0,0,0,0);box.addWidget(item);box.addStretch();stack.addWidget(scroll(page))
    navigation.currentRowChanged.connect(stack.setCurrentIndex);navigation.setCurrentRow(0)
    w.settings_navigation=navigation;w.settings_stack=stack
    shell.addWidget(navigation);shell.addWidget(stack,1)
    settings.deleteLater()
    w.pages.addTab(sections,'资源与设置');w.pages.setCurrentIndex(1)
