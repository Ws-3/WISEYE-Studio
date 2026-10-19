import json
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QProcess
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QFileDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QMessageBox)
from core.config import ROOT
from core.scenes import SceneStore


class ImportWorker(QThread):
    result = Signal(str)
    error = Signal(str)

    def __init__(self, store, path, parent):
        super().__init__(parent)
        self.store, self.path = store, path

    def run(self):
        try:
            scene = self.store.import_pack(self.path)
            self.result.emit('已导入：' + scene['name'] + '。请重启 UE 后使用。')
        except Exception as exc:
            self.error.emit(str(exc))


class SceneForm(QDialog):
    def __init__(self, store, parent):
        super().__init__(parent)
        self.setWindowTitle('接入 UE 场景')
        self.store = store
        layout = QVBoxLayout(self)
        note = QLabel('先在 UE 中导入或迁移 Fab / 社区资源，保存并关闭 UE。\n系统会创建场景副本并安装标准设备；原地图保留。\nWorld Partition 地图请按场景接入文档操作。')
        layout.addWidget(note)
        form = QFormLayout()
        layout.addLayout(form)
        self.identifier = QLineEdit()
        self.identifier.setPlaceholderText('例如 city_day')
        self.title = QLineEdit()
        self.maps = QComboBox()
        self.maps.addItem('新建空白测试场', '')
        for file in sorted((store.project / 'Content').rglob('*.umap')):
            path = '/Game/' + file.relative_to(store.project / 'Content').with_suffix('').as_posix()
            self.maps.addItem(path, path)
        form.addRow('场景 ID', self.identifier)
        form.addRow('显示名称', self.title)
        form.addRow('源地图', self.maps)
        self.fields = {}
        for key, title, values in [
            ('gimbal_location_cm', '云台位置 X / Y / Z（cm）', [0, 0, 3.0585]),
            ('flight_origin_cm', '航线中心 X / Y / Z（cm）', [-1800, 0, 600]),
            ('overview_location_cm', '总览位置 X / Y / Z（cm）', [-2600, -2000, 1400]),
            ('overview_rotation_deg', '总览俯仰 / 偏航 / 滚转（°）', [-20, 40, 0])]:
            row = QHBoxLayout()
            spins = []
            for value in values:
                spin = QDoubleSpinBox()
                spin.setRange(-1e8, 1e8)
                spin.setDecimals(4)
                spin.setValue(value)
                row.addWidget(spin)
                spins.append(spin)
            self.fields[key] = spins
            form.addRow(title, row)
        for key, title, value, low, high in [('flight_radius_cm', '航线半径（cm）', 600, 1, 1e6),
            ('period_s', '航线周期（秒）', 24, 1, 86400), ('vertical_amplitude_cm', '升降幅度（cm）', 150, 0, 1e6),
            ('fov_deg', '相机水平视场（°）', 25, 5, 120)]:
            spin = QDoubleSpinBox()
            spin.setRange(low, high)
            spin.setValue(value)
            self.fields[key] = spin
            form.addRow(title, spin)
        button = QPushButton('保存配置，准备场景')
        button.clicked.connect(self.save)
        layout.addWidget(button)

    def save(self):
        try:
            identifier = self.identifier.text().strip()
            self.scene = dict(version=1, id=identifier, name=self.title.text().strip(),
                              map=f'/Game/WISEYE/Scenes/{identifier}/Scene', rig='standard_v1')
            for key, widget in self.fields.items():
                self.scene[key] = [spin.value() for spin in widget] if isinstance(widget, list) else widget.value()
            if self.maps.currentData():
                self.scene['source_map'] = self.maps.currentData()
            self.store.register(self.scene, require_map=False)
            self.accept()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, '配置未保存', str(exc))


class SceneDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('WISEYE 地图与场景')
        self.resize(780, 480)
        self.store = SceneStore(ROOT)
        self.worker = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('统一设备 · 独立场景配置 · 原始地图保留'))
        self.listing = QListWidget()
        layout.addWidget(self.listing)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.buttons = []
        for title, callback in [('刷新', self.refresh), ('导入标准场景包', self.import_pack),
                                ('接入 UE / Fab 地图', self.adapt), ('准备所选场景', self.prepare),
                                ('接入说明', self.help)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.buttons.append(button)
        layout.addLayout(row)
        self.refresh()

    def refresh(self):
        self.scenes, errors = self.store.list()
        self.listing.clear()
        for scene in self.scenes:
            self.listing.addItem(f"{scene['name']}  ·  {'地图已安装' if scene['installed'] else '待准备'}\n{scene['map']}")
        self.status.setText('\n'.join(errors) if errors else '导入或准备完成后，回到主窗口选择场景。新增资源需重新打开 UE。')
        self.parent().refresh_scenes()

    def import_pack(self):
        path, _ = QFileDialog.getOpenFileName(self, '导入 WISEYE 场景包', '', 'WISEYE 场景包 (*.zip)')
        if not path:
            return
        self.worker = ImportWorker(self.store, path, self)
        self.worker.result.connect(self.import_done)
        self.worker.error.connect(lambda message: self.status.setText('导入失败：' + message))
        self.worker.finished.connect(lambda: [button.setEnabled(True) for button in self.buttons])
        for button in self.buttons:
            button.setEnabled(False)
        self.status.setText('正在后台校验和导入场景包…')
        self.worker.start()

    def import_done(self, message):
        self.refresh()
        self.status.setText(message)

    def adapt(self):
        form = SceneForm(self.store, self)
        if form.exec():
            self.refresh()
            self.launch_prepare(form.scene['id'])

    def prepare(self):
        i = self.listing.currentRow()
        if i < 0:
            self.status.setText('请先选择场景')
            return
        if self.scenes[i]['installed']:
            self.status.setText('地图已经存在，不会覆盖；请打开 UE 检查或使用新场景 ID。')
            return
        self.launch_prepare(self.scenes[i]['id'])

    def launch_prepare(self, identifier):
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(lambda: self.status.setText(bytes(self.process.readAllStandardOutput()).decode(errors='replace')[-1200:]))
        self.process.finished.connect(lambda code, _: self.status.setText('已打开 UE 准备场景，请检查输出日志与地图，成功保存后刷新列表。' if code == 0 else '准备启动失败。请保存并关闭全部 UE 后重试；详细原因见上方输出或终端。'))
        self.process.start('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                           str(ROOT/'scripts/Start-WISEYE.ps1'), '-SkipBuild', '-PrepareScene', identifier])
        self.status.setText('正在启动场景准备工具…')

    def help(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ROOT/'docs/SCENES.md')))

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.status.setText('导入仍在进行，请等待完成后关闭。')
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
            return
        super().closeEvent(event)
