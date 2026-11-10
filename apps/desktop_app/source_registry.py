"""Stable sensor identity, independent of property or control selection."""
from dataclasses import dataclass

SENSOR_NAMES = {'visible': '可见光', 'infrared': '红外', 'lidar': '激光点云', 'event':'事件相机', 'observer': 'UE 观察','aerial':'机载可见光','aerial_infrared':'机载红外'}
SIZES = {'visible': (1920, 1080), 'infrared': (640, 512), 'event':(640,480), 'observer': (960, 540),'aerial':(1920,1080),'aerial_infrared':(640,512)}


@dataclass(frozen=True)
class Source:
    device_id: str
    sensor_id: str

    @property
    def key(self):
        return self.device_id + '/' + self.sensor_id

    @property
    def title(self):
        return ('UE 观察视角' if self.sensor_id == 'observer'
                else self.device_id + ' · ' + SENSOR_NAMES[self.sensor_id])

    def url(self, host, config):
        if self.sensor_id in ('lidar','event','aerial','aerial_infrared'):
            return ''
        return config.stream_url(self.device_id, self.sensor_id)

    @classmethod
    def parse(cls, key):
        device, sensor = key.split('/', 1)
        if sensor not in SENSOR_NAMES or not device or len(key) > 100:
            raise ValueError('无效画面源')
        if sensor == 'observer' and device != 'scene':
            raise ValueError('观察源必须属于场景')
        return cls(device, sensor)


DEFAULT_SOURCES = ['scene/observer', 'ptz-01/visible', 'ptz-01/infrared', 'ptz-01/lidar', 'ptz-01/event']
