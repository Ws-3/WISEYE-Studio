from dataclasses import dataclass
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class AppConfig:
    host: str = '127.0.0.1'
    port: int = 50051
    poll_ms: int = 500
    timeout_ms: int = 5000

    @classmethod
    def load(cls, path: Path | None = None):
        values = json.loads((path or ROOT/'configs/app.json').read_text(encoding='utf-8-sig'))
        config = cls(**values)
        if not config.host or not 1024 <= config.port <= 65535 or config.poll_ms < 100 or config.timeout_ms < 1000:
            raise ValueError('连接配置无效：请检查 host、port、poll_ms 和 timeout_ms')
        return config
