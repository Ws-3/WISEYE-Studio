"""Fixed-source, shared latest-frame previews and local layout persistence."""
import json
import time
from PySide6.QtCore import Qt, QTimer, QSettings, QMimeData, Signal, QPoint
from PySide6.QtGui import QDrag, QPixmap
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QComboBox, QMenu, QDialog, QScrollArea, QSizePolicy, QTreeWidget, QSplitter)
from apps.desktop_app.source_registry import Source, SIZES, DEFAULT_SOURCES
from apps.desktop_app.ue_preview_client import UEPreviewClient
from apps.desktop_app.lidar_view import LidarView
from apps.desktop_app.observer_input import ObserverInput


class DragLabel(QLabel):
    selected = Signal()

    def mousePressEvent(self, event):
        self.origin = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton and
                (event.position().toPoint() - getattr(self, 'origin', QPoint())).manhattanLength() > 12):
            mime = QMimeData()
            mime.setData('application/x-wiseye-source', self.property('sourceKey').encode())
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)


class SourceTree(QTreeWidget):
    def startDrag(self, actions):
        item=self.currentItem()
        value=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        if not value or value[0]!='sensor':return
        mime=QMimeData();mime.setData('application/x-wiseye-source',value[1].encode())
        drag=QDrag(self);drag.setMimeData(mime);drag.exec(Qt.DropAction.CopyAction)


class SourceTile(QFrame):
    def __init__(self, workspace, key):
        super().__init__()
        self.workspace, self.key = workspace, key
        self.setObjectName('viewTile')
        self.setAcceptDrops(True)
        self.setMinimumSize(120, 100)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-wiseye-source'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        key = bytes(event.mimeData().data('application/x-wiseye-source')).decode('utf-8')
        if key in self.workspace.sources:self.workspace.swap(key,self.key)
        else:self.workspace.add_source(key,replace=self.key)
        event.acceptProposedAction()


class SensorWorkspace(QWidget):
    def __init__(self, window, image_type):
        super().__init__()
        self.window, self.image_type = window, image_type
        self.sources = list(DEFAULT_SOURCES)
        self.registry = {key: Source.parse(key) for key in self.sources}
        self.cards, self.views, self.headers, self.meta = {}, {}, {}, {}
        self.clients, self.frames, self.popouts, self.clouds = {}, {}, {}, {}
        self.states, self.samples, self.fps, self.messages = {}, {}, {}, {}
        self.received, self.missing = {}, set()
        self.run_id = None
        self.expanded = None
        self.settings = QSettings('WISEYE', 'Studio')
        self._load()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)
        top = QHBoxLayout()
        caption=QLabel('VIEWPORT');caption.setObjectName('section');top.addWidget(caption)
        self.layout_choice = QComboBox()
        for label, mode in [('场景主导', 'scene'), ('双模态对比', 'dual'), ('多源监看', 'grid'), ('自定义主画面', 'custom')]:
            self.layout_choice.addItem(label, mode)
        self.layout_choice.setCurrentIndex(max(0, self.layout_choice.findData(self.mode)))
        self.layout_choice.activated.connect(self.change_layout)
        top.addWidget(self.layout_choice)
        top.addStretch()
        self.add_button = QPushButton('添加画面')
        self.add_menu = QMenu(self.add_button)
        self.add_button.setMenu(self.add_menu)
        self.add_menu.aboutToShow.connect(self.build_add_menu)
        top.addWidget(self.add_button)
        reset = QPushButton('恢复布局')
        reset.setObjectName('ghost')
        reset.clicked.connect(self.reset_layout)
        top.addWidget(reset)
        outer.addLayout(top)
        self.body = QWidget()
        self.grid = QGridLayout(self.body)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        outer.addWidget(self.body, 1)
        self.scene_split=QSplitter(Qt.Orientation.Vertical)
        hero=QWidget();thumbs=QWidget()
        self.hero_layout=QVBoxLayout(hero);self.hero_layout.setContentsMargins(0,0,0,0)
        self.thumb_layout=QHBoxLayout(thumbs);self.thumb_layout.setContentsMargins(0,0,0,0);self.thumb_layout.setSpacing(8)
        self.scene_split.addWidget(hero);self.scene_split.addWidget(thumbs)
        self.scene_split.setChildrenCollapsible(False)
        self.scene_split.splitterMoved.connect(self.split_moved)
        outer.addWidget(self.scene_split,1)
        self.empty = QLabel('暂无画面；点击“添加画面”选择设备传感器。', self.body)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note = QLabel('拖动画面标题交换位置；选择属性与控制对象互相独立。')
        self.note.setObjectName('muted')
        self.note.setWordWrap(True)
        outer.addWidget(self.note)
        class ObserverView(ObserverInput, image_type):
            def __init__(view):
                image_type.__init__(view)
                view.init_observer(window)
        self.observer_type = ObserverView
        self.arrange()
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.last_state_poll = 0.
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.point_timer = QTimer(self)
        self.point_timer.setInterval(100)
        self.point_timer.timeout.connect(self.poll_points)
        self.point_timer.start()
        window.client.state_received.connect(self.observe)
        window.client.completed.connect(self.completed)

    def _load(self):
        self.mode = 'scene'
        self.scene_sizes=[700,300]
        try:
            data = json.loads(self.settings.value('workspace/v3', '{}'))
            keys = data.get('sources', DEFAULT_SOURCES)
            if not isinstance(keys, list) or len(keys) > 4 or len(set(keys)) != len(keys):
                raise ValueError()
            self.sources = [Source.parse(key).key for key in keys]
            self.registry.update({key: Source.parse(key) for key in self.sources})
            if data.get('mode') in ('scene', 'dual', 'grid', 'custom'):
                self.mode = data['mode']
            sizes=data.get('scene_sizes')
            if isinstance(sizes,list) and len(sizes)==2 and all(type(v) is int and 1<=v<=10000 for v in sizes):self.scene_sizes=sizes
        except (TypeError, ValueError, AttributeError):
            pass

    def save_layout(self):
        self.settings.setValue('workspace/v3', json.dumps(dict(sources=self.sources, mode=self.mode,scene_sizes=self.scene_sizes)))

    def split_moved(self,*_):
        sizes=self.scene_split.sizes()
        if all(sizes):self.scene_sizes=sizes;self.save_layout()

    def reset_layout(self):
        self.sources = list(DEFAULT_SOURCES)
        self.expanded = None
        self.mode = 'scene'
        self.scene_sizes=[700,300]
        self.layout_choice.setCurrentIndex(0)
        self.arrange()

    def change_layout(self):
        self.mode = self.layout_choice.currentData()
        self.expanded = None
        if self.mode == 'dual':
            # An explicit preset chooses a pair; later object selection cannot change it.
            device = self.window.selected_gimbal
            self.sources = [device + '/visible', device + '/infrared']
        elif self.mode == 'scene' and 'scene/observer' not in self.sources:
            self.sources = ['scene/observer'] + self.sources[:3]
        self.arrange()

    def add_source(self, key, replace=None):
        try:
            source = Source.parse(key)
        except (ValueError, AttributeError):
            return
        if key in self.sources:
            return
        candidate=list(self.sources)
        if replace in candidate:candidate[candidate.index(replace)]=key
        else:candidate.append(key)
        if len(set(candidate)|set(self.popouts))>4:
            self.window.log('最多同时订阅四个本地画面源；请先关闭被替换来源的弹窗，或移除其他画面。')
            return
        if replace in self.sources:
            self.sources[self.sources.index(replace)] = key
        elif len(self.sources) < 4:
            self.sources.append(key)
        else:
            self.window.log('最多同时显示四路；请从“替换画面源”选择要替换的位置。')
            return
        self.registry[key] = source
        self.expanded = None
        self.arrange()

    def build_add_menu(self):
        self.add_menu.clear()
        for key, source in self.registry.items():
            if source.sensor_id != 'observer' and source.device_id in self.missing:
                continue
            action = self.add_menu.addAction(source.title)
            action.setEnabled(key not in self.sources and len(self.sources) < 4)
            action.triggered.connect(lambda _, k=key: self.add_source(k))
        if len(self.sources) == 4:
            info = self.add_menu.addAction('四路已满：在画面“更多”中替换或移除')
            info.setEnabled(False)

    def remove_source(self, key):
        if key in self.popouts:
            self.popouts[key][0].close()
        if key in self.sources:
            self.sources.remove(key)
        self.expanded = None
        self.arrange()

    def swap(self, a, b):
        if a in self.sources and b in self.sources:
            i, j = self.sources.index(a), self.sources.index(b)
            self.sources[i], self.sources[j] = self.sources[j], self.sources[i]
            if self.mode == 'scene':
                self.mode = 'custom'
                self.layout_choice.setCurrentIndex(3)
            self.arrange()

    def make_view(self, key):
        source = self.registry[key]
        view = LidarView() if source.sensor_id == 'lidar' else self.observer_type() if source.sensor_id == 'observer' else self.image_type()
        view.setMinimumSize(100, 60)
        view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        return view

    def make_tile(self, key):
        source = self.registry.setdefault(key, Source.parse(key))
        card = SourceTile(self, key)
        box = QVBoxLayout(card)
        box.setContentsMargins(10, 8, 10, 6)
        box.setSpacing(4)
        top = QHBoxLayout()
        channel=QLabel({'observer':'SCENE','visible':'EO','infrared':'IR','lidar':'LIDAR'}[source.sensor_id]);channel.setObjectName('channel');top.addWidget(channel)
        title = DragLabel(source.title);title.setObjectName('tileTitle')
        title.setProperty('sourceKey', key)
        title.setToolTip(key + ' · 拖动可交换位置，点击选择属性')
        title.selected.connect(lambda: self.select_properties(key))
        top.addWidget(title, 1)
        from apps.desktop_app.ui.icons import icon
        zoom = QPushButton();zoom.setIcon(icon('expand'));zoom.setFixedWidth(32);zoom.setAccessibleName('放大画面')
        zoom.setObjectName('iconButton')
        zoom.setToolTip('在工作区放大；再次点击返回布局')
        zoom.clicked.connect(lambda: self.maximize(key))
        more = QPushButton('···');more.setFixedWidth(38);more.setToolTip('画面操作');more.setAccessibleName('画面操作')
        more.setObjectName('iconButton')
        menu = QMenu(more)
        more.setMenu(menu)
        menu.aboutToShow.connect(lambda: self.build_tile_menu(key, menu))
        top.addWidget(zoom)
        top.addWidget(more)
        box.addLayout(top)
        view = self.make_view(key)
        box.addWidget(view, 1)
        meta = QLabel(self.base_info(key))
        meta.setObjectName('streamMeta')
        meta.setMaximumHeight(38)
        meta.setToolTip(self.base_info(key))
        box.addWidget(meta)
        self.cards[key], self.views[key], self.meta[key], self.headers[key] = card, view, meta, zoom

    def base_info(self, key):
        source = self.registry[key]
        dims = SIZES.get(source.sensor_id)
        return key + (' · ' + '×'.join(map(str, dims)) if dims else ' · 单帧 · 米制')

    def build_tile_menu(self, key, menu):
        menu.clear()
        source = self.registry[key]
        if source.sensor_id == 'observer':
            menu.addAction('接管自由观察', self.activate_observer)
        else:
            action = menu.addAction('保存原始单帧', lambda: self.window.capture_source(source.device_id, source.sensor_id))
            action.setEnabled(self.window.client.ready and self.source_enabled(key) and key not in self.messages)
            menu.addAction('编辑此传感器参数', lambda: self.select_properties(key))
        menu.addAction('弹出窗口', lambda: self.enlarge(key))
        if source.sensor_id != 'lidar':
            menu.addAction('原始像素查看', lambda: self.enlarge(key, native=True))
        replace = menu.addMenu('替换画面源')
        for other, item in self.registry.items():
            if other not in self.sources and item.device_id not in self.missing:
                replace.addAction(item.title, lambda k=other: self.add_source(k, key))
        menu.addAction('移出工作区', lambda: self.remove_source(key))

    def select_properties(self, key):
        source = self.registry[key]
        if source.sensor_id == 'observer':
            return
        from apps.desktop_app.workbench_v3 import show_properties
        show_properties(self.window, 'sensor', source.device_id + '/' + source.sensor_id)

    def maximize(self, key):
        self.expanded = None if self.expanded == key else key
        self.arrange()

    def arrange(self):
        for card in self.cards.values():
            self.grid.removeWidget(card)
            self.hero_layout.removeWidget(card)
            self.thumb_layout.removeWidget(card)
            card.hide()
        self.grid.removeWidget(self.empty)
        self.empty.hide()
        for index in range(4):
            self.grid.setRowStretch(index, 0)
            self.grid.setColumnStretch(index, 0)
        active = [self.expanded] if self.expanded in self.sources else self.sources
        scene_mode=self.mode in ('scene','custom') and not self.expanded and len(active)>1
        self.body.setVisible(not scene_mode)
        self.scene_split.setVisible(scene_mode)
        for key in active:
            if key not in self.cards:
                self.make_tile(key)
        if not active:
            self.grid.addWidget(self.empty, 0, 0)
            self.empty.show()
        elif len(active) == 1:
            self.grid.addWidget(self.cards[active[0]], 0, 0)
            self.grid.setRowStretch(0, 1)
        elif scene_mode:
            hero = 'scene/observer' if self.mode == 'scene' and 'scene/observer' in active else active[0]
            rest = [k for k in active if k != hero]
            self.hero_layout.addWidget(self.cards[hero])
            for index, key in enumerate(rest):
                self.thumb_layout.addWidget(self.cards[key],1)
            self.scene_split.setSizes(self.scene_sizes)
        else:
            for index, key in enumerate(active):
                self.grid.addWidget(self.cards[key], index // 2, index % 2)
                self.grid.setRowStretch(index // 2, 1)
                self.grid.setColumnStretch(index % 2, 1)
        for key in active:
            self.cards[key].show()
            self.headers[key].setText('')
            self.headers[key].setToolTip('返回布局' if key == self.expanded else '放大画面')
        # Deleted panels do not retain image copies, renderers or QObject children.
        for key in list(self.cards):
            if key not in self.sources:
                self.cards.pop(key).deleteLater()
                self.views.pop(key, None)
                self.meta.pop(key, None)
                self.headers.pop(key, None)
        self.save_layout()
        if hasattr(self.window, 'host'):
            self.sync_clients()

    def activate_observer(self):
        self.window.command('input.set_mode', {'mode': 'observer'})
        self.window.command('observer.set_mode', {'mode': 'free'})
        view = self.views.get('scene/observer')
        if view:
            view.setFocus()

    def wanted(self):
        return set(self.sources) | set(self.popouts)

    def displayed(self):
        return (set(self.sources) if self.window.pages.currentIndex()==1 else set()) | set(self.popouts)

    def source_enabled(self, key):
        source = self.registry[key]
        return (source.device_id not in self.missing and
                self.states.get(source.device_id, {}).get('sensors', {}).get(source.sensor_id, {}).get('enabled', True))

    def sync_clients(self):
        ready = self.window.client.ready
        host = self.window.host.text().strip() or self.window.config.host
        wanted = {key for key in self.displayed() if self.registry[key].sensor_id != 'lidar' and self.source_enabled(key)} if ready else set()
        for key in list(self.clients):
            if key not in wanted:
                client = self.clients.pop(key)
                client.stop()
                client.deleteLater()
                self.frames.pop(key, None)
        for key in wanted:
            source = self.registry[key]
            if key not in self.clients:
                client = UEPreviewClient(self, size=SIZES[source.sensor_id])
                client.frame_received.connect(lambda image, fps, k=key: self.frame(k, image))
                client.state_changed.connect(lambda connected, msg, k=key: self.stream_state(k, connected, msg))
                self.clients[key] = client
            channel = {'visible': 'CH1', 'infrared': 'CH2', 'observer': 'OBS'}[source.sensor_id]
            self.clients[key].start_source(host, self.window.config.port, channel,
                                           None if channel == 'OBS' else source.device_id)

    def stream_state(self, key, connected, message):
        if not connected:
            self.unavailable(key, message)

    def frame(self, key, image):
        if not self.source_enabled(key):
            return
        self.messages.pop(key, None)
        self.frames[key] = image
        self.received[key] = time.monotonic()
        for view in self.targets(key):
            view.show_image(image)

    def targets(self, key):
        result = [self.views[key]] if key in self.views else []
        if key in self.popouts:
            result.append(self.popouts[key][1])
        return result

    def unavailable(self, key, message):
        self.messages[key] = message
        self.frames.pop(key, None)
        for view in self.targets(key):
            if self.registry[key].sensor_id == 'lidar':
                view.show_unavailable(message)
            else:
                view.source = QPixmap()
                view.clear()
                view.setText(message)
                if hasattr(view, 'stop'):
                    view.stop()
        if key in self.meta:
            text=self.base_info(key)+' · '+message
            label=self.meta[key]
            label.setText(label.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,max(80,label.width())))
            label.setToolTip(text)

    def observe(self, state):
        run = state.get('run_id')
        if run and self.run_id and self.run_id != run:
            self.disconnected()
            self.states.clear()
            self.samples.clear()
            self.fps.clear()
        self.run_id = run
        device = state.get('gimbal_id', 'ptz-01')
        self.states[device] = state
        devices = state.get('devices', [])
        ids = {d['id'] for d in devices}
        self.missing = {s.device_id for s in self.registry.values() if s.sensor_id != 'observer' and s.device_id not in ids} if devices else set()
        for item in devices:
            if item['kind'] == 'gimbal':
                for sensor in ('visible', 'infrared', 'lidar'):
                    source = Source(item['id'], sensor)
                    self.registry[source.key] = source
        now = time.monotonic()
        for channel, sensor in [('CH1', 'visible'), ('CH2', 'infrared'), ('OBS', 'observer')]:
            key = 'scene/observer' if sensor == 'observer' else device + '/' + sensor
            info = state.get('streams', {}).get(channel, {})
            count = info.get('completed_frames')
            previous = self.samples.get(key)
            if count is not None:
                if previous and now - previous[0] >= 2:
                    self.fps[key] = max(0, count - previous[1]) / (now - previous[0])
                    self.samples[key] = now, count
                elif not previous:
                    self.samples[key] = now, count
        for key in self.wanted():
            source = self.registry[key]
            if source.device_id in self.missing:
                self.unavailable(key, '来源不存在 · 请移除或替换')
            elif source.device_id == device and not self.source_enabled(key):
                self.unavailable(key, '传感器已停用')
        self.sync_clients()

    def completed(self, command, state):
        if command != 'sensor.lidar.get_points':
            return
        key = state.get('gimbal_id', 'ptz-01') + '/lidar'
        if key not in self.wanted() or not self.source_enabled(key):
            return
        cloud = (state.get('lidar_points_m', []), state.get('lidar_point_count', 0), state.get('lidar_rays', 0))
        self.clouds[key] = cloud
        self.received[key] = time.monotonic()
        self.messages.pop(key, None)
        for view in self.targets(key):
            view.set_points(*cloud)

    def refresh(self):
        if not self.window.client.ready:
            return
        # The main connection already polls the selected PTZ. Other displayed PTZs
        # receive explicit addressed state queries, never an input.select command.
        payloads = getattr(self.window.client, 'request_payloads', {})
        pending = list(payloads.values())
        if time.monotonic()-self.last_state_poll >= 1:
            self.last_state_poll=time.monotonic()
            observed={self.registry[k].device_id for k in self.displayed() if self.registry[k].sensor_id!='observer'}
            if self.window.pages.currentIndex()==2:
                observed|={source.device_id for source in self.registry.values() if source.sensor_id!='observer'}
            if self.window.pages.currentIndex()==1 and self.window.inspectors.currentIndex()==2:
                observed.add(self.window.sensor_settings.device_id)
            for device in observed - self.missing:
                if device != self.window.selected_gimbal and not any(c == 'sim.get_state' and p.get('device_id') == device for c, p in pending):
                    self.window.client.request('sim.get_state', {'device_id': device})
        for key in self.wanted():
            source = self.registry[key]
            label = self.meta.get(key)
            if label:
                text = self.base_info(key)
                if key in self.messages:
                    text += ' · ' + self.messages[key]
                elif source.sensor_id != 'lidar':
                    fps = self.fps.get(key)
                    text += ' · 新帧 ' + (f'{fps:.1f} Hz' if fps is not None else '未测量')
                if key in self.received:
                    text += f' · 接收于 {max(0, time.monotonic()-self.received[key]):.1f}s 前'
                label.setText(label.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, max(80,label.width())))
                label.setToolTip(text)

    def poll_points(self):
        if not self.window.client.ready:
            return
        pending = self.window.client.request_payloads.values()
        for key in self.displayed():
            source = self.registry[key]
            if source.sensor_id == 'lidar' and self.source_enabled(key):
                if not any(c == 'sensor.lidar.get_points' and p.get('device_id') == source.device_id
                           for c, p in pending):
                    self.window.client.request('sensor.lidar.get_points', {'device_id': source.device_id})

    def enlarge(self, key, native=False):
        if key in self.popouts:
            dialog,view=self.popouts[key]
            if bool(getattr(view,'native_pixels',False))==native:
                dialog.show();dialog.raise_();return
            dialog.close()
        dialog = QDialog(self.window)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle('WISEYE · ' + self.registry[key].title)
        screen = self.window.screen().availableGeometry()
        dialog.resize(min(1100, screen.width()-60), min(760, screen.height()-60))
        box = QVBoxLayout(dialog)
        box.addWidget(QLabel(self.base_info(key) + (' · 原始像素' if native else ' · 适应窗口')))
        view = self.make_view(key)
        if native and self.registry[key].sensor_id != 'lidar':
            view.native_pixels = True
            view.setFixedSize(*SIZES[self.registry[key].sensor_id])
            area = QScrollArea()
            area.setWidget(view)
            box.addWidget(area, 1)
        else:
            box.addWidget(view, 1)
        self.popouts[key] = dialog, view
        dialog.finished.connect(lambda _: self.popout_closed(key))
        if key in self.frames:
            view.show_image(self.frames[key])
        elif key in self.clouds:
            view.set_points(*self.clouds[key])
        else:
            self.unavailable(key, self.messages.get(key, '等待首帧'))
        dialog.show()
        self.sync_clients()

    def popout_closed(self, key):
        self.popouts.pop(key, None)
        self.sync_clients()

    def disconnected(self):
        for client in self.clients.values():
            client.stop()
            client.deleteLater()
        self.clients.clear()
        self.frames.clear()
        self.received.clear()
        self.clouds.clear()
        for key in self.wanted():
            self.unavailable(key, '仿真未连接')

    def close_popouts(self):
        for dialog, _ in list(self.popouts.values()):
            dialog.close()

    def shutdown(self):
        self.timer.stop()
        self.point_timer.stop()
        self.close_popouts()
        self.disconnected()
