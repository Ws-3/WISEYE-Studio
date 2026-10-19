from dataclasses import dataclass
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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

    @classmethod
    def load(cls, path: Path | None = None):
        values = json.loads((path or ROOT/'configs/app.json').read_text(encoding='utf-8-sig'))
        config = cls(**values)
        if (not config.host or not 1024 <= config.port <= 65535
                or not 1024 <= config.airsim_port <= 65535
                or not 1024 <= config.rtsp_port <= 65535
                or config.poll_ms < 100 or config.timeout_ms < 1000
                or not 1 <= config.rtsp_visible_fps <= 60
                or not 1 <= config.rtsp_infrared_fps <= 60
                or not 25 <= config.rtsp_jpeg_quality <= 95
                or not config.rtsp_visible_path or not config.rtsp_infrared_path):
            raise ValueError('连接配置无效：请检查 UE、AirSim 和 RTSP 配置')
        return config
