"""Opt-in PIE test bridge; accepts only start/stop for the fixed latency fixture.

In UE's command console: py <repo>/ue5/scripts/latency_probe_bridge.py
"""
import json, math, runpy, traceback
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / 'runtime/latency-probe-request.json'
unreal.EditorPythonScripting.set_keep_python_script_alive(True)

def tick(dt):
    if not REQUEST.exists():
        return
    try:
        request = json.loads(REQUEST.read_text(encoding='utf8'))
        REQUEST.unlink()
        origin = request['origin']
        if type(origin) not in (float, int) or not math.isfinite(origin):
            raise ValueError('Invalid test clock origin')
        probe = getattr(unreal, '_wise_latency_probe', None)
        if request['command'] == 'start':
            if probe:
                raise RuntimeError('Another probe is already active')
            (ROOT / 'runtime/latency_probe_config.json').write_text(json.dumps(dict(origin=origin)))
            runpy.run_path(str(ROOT / 'ue5/scripts/probe_video_latency.py'))
        elif request['command'] == 'stop':
            if probe and probe.origin == origin:
                probe.close()
        else:
            raise ValueError('Only start/stop are supported')
    except Exception:
        (ROOT / 'logs/latency_probe_error.txt').write_text(traceback.format_exc(), encoding='utf8')
        unreal.log_error(traceback.format_exc())

if getattr(unreal, '_wise_latency_bridge', None):
    unreal.unregister_slate_post_tick_callback(unreal._wise_latency_bridge)
unreal._wise_latency_bridge = unreal.register_slate_post_tick_callback(tick)
unreal.log('WISEYE opt-in latency fixture bridge ready')
