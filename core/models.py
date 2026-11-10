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
    if state.get('active_sensor', state.get('sensor_mode')) not in ('visible', 'infrared', 'lidar'):
        raise ProtocolError('光电云台工作传感器无效')
    dimensions = (state.get('width'), state.get('height'))
    selected = state.get('sensor_mode')
    sensors = state.get('sensors')
    sensor = sensors.get(selected, {}) if isinstance(sensors, dict) else {}
    # Older native builds report no render target when the selected camera is
    # off. This is a valid power state, not a broken control connection.
    disabled_legacy = dimensions == (0, 0) and isinstance(sensor, dict) and sensor.get('enabled') is False
    if dimensions not in ((1920, 1080), (640, 512)) and not disabled_legacy:
        raise ProtocolError('相机分辨率无效')
    if state.get('drone_model', 'mavic3') not in ('mavic3', 'avata', 'fixedwing'):
        raise ProtocolError('无人机型号无效')
    position = state.get('drone_position_cm')
    if not isinstance(position, list) or len(position) != 3 or not all(type(v) in (int, float) and math.isfinite(v) for v in position):
        raise ProtocolError('无人机位置无效')
    return state

def validate_airsim_state(state):
    if state.get('application') != 'WISEYE AirSim Control':
        raise ProtocolError('服务不是 WISEYE AirSim Control')
    for key in ('connected', 'paused', 'command_active'):
        if type(state.get(key)) is not bool:
            raise ProtocolError(f'AirSim 状态字段 {key} 无效')
    if state.get('flight_mode') not in ('auto', 'manual'):
        raise ProtocolError('AirSim 飞行模式无效')
    for key in ('route_loops', 'velocity_mps'):
        value = state.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ProtocolError(f'AirSim 状态字段 {key} 无效')
    position = state.get('position_ned_m')
    if not isinstance(position, list) or len(position) != 3 or not all(
            type(v) in (int, float) and math.isfinite(v) for v in position):
        raise ProtocolError('AirSim 无人机位置无效')
    if not isinstance(state.get('last_error'), str):
        raise ProtocolError('AirSim 错误状态无效')
    return state
