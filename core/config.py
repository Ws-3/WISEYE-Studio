from dataclasses import dataclass, asdict, field
import json
import os
import re
import tempfile
from pathlib import Path

from core.runtime_paths import DATA_ROOT, initialize_data

initialize_data()
ROOT = DATA_ROOT

@dataclass(frozen=True)
class AppConfig:
    host: str = '127.0.0.1'
    port: int = 50051
    airsim_port: int = 50052
    poll_ms: int = 500
    timeout_ms: int = 5000
    rtsp_port: int = 8554
    rtsp_visible_path: str = 'CH1'
    rtsp_infrared_path: str = 'CH2'
    rtsp_visible_fps: int = 30
    rtsp_infrared_fps: int = 25
    rtsp_jpeg_quality: int = 60
    rtsp_host: str = '127.0.0.1'
    rtsp_observer_path: str = 'OBS'
    rtsp_paths: dict[str, str] = field(default_factory=dict)

    def stream_path(self, device_id, sensor_id):
        key = f'{device_id}/{sensor_id}'
        default = (self.rtsp_observer_path if sensor_id == 'observer' else
                   ('' if device_id == 'ptz-01' else device_id + '/') +
                   (self.rtsp_visible_path if sensor_id == 'visible' else self.rtsp_infrared_path))
        return self.rtsp_paths.get(key, default)

    def stream_url(self, device_id, sensor_id):
        return f'rtsp://{self.rtsp_host}:{self.rtsp_port}/{self.stream_path(device_id, sensor_id)}'

    def validate(self):
        if not isinstance(self.rtsp_paths, dict):
            raise ValueError('RTSP 路径覆盖必须是设备/传感器到路径的字典。')
        if (not re.fullmatch(r'[A-Za-z0-9.-]+', self.host)
                or not re.fullmatch(r'[A-Za-z0-9.-]+', self.rtsp_host)
                or any(type(p) is not int or not 1024 <= p <= 65535 for p in (self.port, self.airsim_port, self.rtsp_port))
                or len({self.port, self.airsim_port, self.rtsp_port}) != 3
                or self.poll_ms < 100 or self.timeout_ms < 1000
                or not 1 <= self.rtsp_visible_fps <= 60 or not 1 <= self.rtsp_infrared_fps <= 60
                or not 25 <= self.rtsp_jpeg_quality <= 95):
            raise ValueError('地址请填写主机名或 IPv4（不含协议/路径），端口须为不同的 1024–65535。请检查帧率与质量。')
        paths = [self.rtsp_visible_path, self.rtsp_infrared_path, self.rtsp_observer_path, *self.rtsp_paths.values()]
        if any(not isinstance(p, str) or len(p) > 160 or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', p) for p in paths):
            raise ValueError('流路径只能包含英文字母、数字、短横线、下划线和分隔斜杠，不含协议、空格或首尾斜杠。')
        keys = {'scene/observer'} | {f'ptz-{n:02}/{s}' for n in range(1, 5) for s in ('visible', 'infrared')}
        if not isinstance(self.rtsp_paths, dict) or set(self.rtsp_paths) - keys:
            raise ValueError('流覆盖必须对应 scene/observer 或 ptz-01～04 的 visible/infrared。')
        effective = [self.stream_path(*key.split('/')) for key in keys]
        if len(set(effective)) != len(effective):
            raise ValueError('不同设备与传感器不能使用相同 RTSP 流路径。')
        return self

    def save(self, path: Path | None = None):
        self.validate()
        target = path or ROOT/'configs/app.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='.app-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as output:
                json.dump(asdict(self), output, ensure_ascii=False, indent=2)
                output.write('\n')
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def write_mediamtx(self, path: Path):
        self.validate()
        # Writable runtime config; no edits to the read-only release resources.
        settings = dict(logLevel='info', rtspAddress=f':{self.rtsp_port}', rtspTransports=['tcp'],
                        rtmp=False, hls=False, webrtc=False, srt=False, playback=False,
                        paths={'all_others': {'source': 'publisher'}})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2), encoding='utf-8')
        return path

    @classmethod
    def load(cls, path: Path | None = None):
        values = json.loads((path or ROOT/'configs/app.json').read_text(encoding='utf-8-sig'))
        return cls(**values).validate()
