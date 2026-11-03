"""Persisted endpoint editor; transport changes never restart an airborne simulation."""
from dataclasses import replace
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QSpinBox, QLabel, QDialogButtonBox, QMessageBox, QCheckBox)
from PySide6.QtNetwork import QAbstractSocket
from core.config import AppConfig


def apply_config(window, config):
    manager = getattr(window, 'runtime_manager', None)
    if ((manager and (getattr(manager, 'processes', []) or getattr(manager, 'running', False)))
            or any(client.socket.state() != QAbstractSocket.SocketState.UnconnectedState
                   for client in (window.client, window.air_client))):
        raise ValueError('请先降落、退出仿真并断开 UE 和飞控连接，再保存接口配置。')
    config.save()
    window.config = config
    for client in (window.client, window.air_client):
        client.config = config
        client.poll.setInterval(config.poll_ms)
    window.air_client.port = config.airsim_port
    window.host.setText(config.host)
    window.port.setValue(config.port)
    window.source_signature = None
    window.source_urls.setPlainText('\n'.join([
        config.stream_url(window.selected_gimbal, 'visible'),
        config.stream_url(window.selected_gimbal, 'infrared'), config.stream_url('scene', 'observer'),
        f'UE / 点云 {config.host}:{config.port}', f'飞控 {config.host}:{config.airsim_port}']))
    window.gallery.sync_clients()
    from apps.desktop_app.workbench_v3 import update_sources
    update_sources(window)


def edit_interfaces(window, source=None):
    dialog = QDialog(window)
    dialog.setWindowTitle('传感器与网络接口' if source is None else source.title + ' · 接口设置')
    dialog.setMinimumWidth(580)
    layout = QVBoxLayout(dialog)
    hint = QLabel('修改后保存到本机配置。视频发布服务下次启动使用新地址；桌面画面仍使用低延迟直连。\n'
                  'UE 控制、云台与点云共用 JSON Lines；控制端口是连接目标，内置仿真仍监听 50051 / 50052。')
    hint.setWordWrap(True); layout.addWidget(hint)
    form = QFormLayout(); fields = {}
    config = window.config
    labels = [('host','UE / 点云主机'), ('port','UE / 点云端口'), ('airsim_port','飞控端口'),
              ('rtsp_host','RTSP 服务主机'), ('rtsp_port','RTSP 服务端口'),
              ('rtsp_visible_path','可见光默认流路径'), ('rtsp_infrared_path','红外默认流路径'),
              ('rtsp_observer_path','观察画面流路径'), ('rtsp_visible_fps','可见光发布 FPS'),
              ('rtsp_infrared_fps','红外发布 FPS'), ('rtsp_jpeg_quality','网关 JPEG 质量')]
    for name, label in labels:
        value = getattr(config, name)
        widget = QSpinBox() if isinstance(value, int) else QLineEdit(value)
        if isinstance(value, int):
            widget.setRange(*( (1024,65535) if 'port' in name else (25,95) if name.endswith('quality') else (1,60)))
            widget.setValue(value)
        fields[name] = widget; form.addRow(label, widget)
    override = None
    use_override = None
    if source and source.sensor_id not in ('lidar','event'):
        use_override = QCheckBox('为此数据源使用独立路径（取消则跟随默认路径）')
        use_override.setChecked(source.key in config.rtsp_paths)
        form.addRow(use_override)
        override = QLineEdit(config.stream_path(source.device_id, source.sensor_id))
        override.setEnabled(use_override.isChecked())
        use_override.toggled.connect(override.setEnabled)
        form.addRow(source.title + ' 路径覆盖', override)
    layout.addLayout(form)
    preview = QLabel(); preview.setWordWrap(True); layout.addWidget(preview)
    def current():
        values = {name: widget.value() if isinstance(widget, QSpinBox) else widget.text().strip()
                  for name, widget in fields.items()}
        paths = dict(config.rtsp_paths)
        if override and use_override.isChecked():
            paths[source.key] = override.text().strip()
        elif source:
            paths.pop(source.key, None)
        return replace(config, **values, rtsp_paths=paths)
    def show_preview():
        candidate = current()
        preview.setText(candidate.stream_url(source.device_id, source.sensor_id)
                        if source and source.sensor_id not in ('lidar','event') else
                        f"{'事件 / sensor.event.get_packet' if source and source.sensor_id=='event' else '点云 / 云台'}：{candidate.host}:{candidate.port}")
    for widget in [*fields.values(), *([override] if override else [])]:
        (widget.valueChanged if isinstance(widget,QSpinBox) else widget.textChanged).connect(show_preview)
    if use_override: use_override.toggled.connect(show_preview)
    show_preview()
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(buttons); buttons.rejected.connect(dialog.reject)
    def save():
        try:
            apply_config(window, current().validate())
        except (ValueError, OSError) as error:
            QMessageBox.warning(dialog, '未保存', str(error)); return
        dialog.accept()
    buttons.accepted.connect(save)
    dialog.exec()
