import math
from core.protocol import ProtocolError

def validate_state(state):
    if state.get('application') != 'WISEYE Studio':
        raise ProtocolError('服务不是 WISEYE Studio')
    for key in ('paused', 'tracking', 'rotors_running'):
        if type(state.get(key)) is not bool:
            raise ProtocolError(f'状态字段 {key} 无效')
    for key in ('simulation_time_s', 'yaw_deg', 'pitch_deg', 'pointing_error_deg', 'fov_deg'):
        value = state.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ProtocolError(f'状态字段 {key} 无效')
    for key, values in [('flight_mode', ('auto', 'manual')), ('sensor_mode', ('visible', 'infrared')),
                        ('palette', ('white_hot', 'black_hot'))]:
        if state.get(key) not in values:
            raise ProtocolError(f'状态字段 {key} 无效')
    if (state.get('width'), state.get('height')) not in ((1920, 1080), (640, 512)):
        raise ProtocolError('相机分辨率无效')
    position = state.get('drone_position_cm')
    if not isinstance(position, list) or len(position) != 3 or not all(type(v) in (int, float) and math.isfinite(v) for v in position):
        raise ProtocolError('无人机位置无效')
    return state
