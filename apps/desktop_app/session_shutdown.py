"""Bounded graceful shutdown, restricted to the simulator run we started."""
import time


def land_owned_fleet(run_id, report=print, timeout=30):
    from core.local_rpc import request
    try:
        state = request(50051, 'sim.get_state')['payload']
        flight = request(50052, 'sim.get_state')['payload']
        if state.get('run_id') != run_id or flight.get('run_id') != run_id:
            report('会话已改变，跳过飞控操作。'); return False
        fleet = flight.get('fleet') or [flight]
        active = [item for item in fleet if item.get('flight_status') != 'ready']
        if not active:return True
        report('正在停止航线并降落无人机…')
        # Resume native simulation first; a paused world cannot finish landing.
        resumed = request(50051, 'sim.resume')
        if resumed.get('status') != 'ok':raise RuntimeError(str(resumed.get('error')))
        deadline = time.monotonic() + timeout
        for item in active:
            payload = {'device_id':item.get('drone_id', item.get('device_id', item.get('id', 'uav-01')))}
            try:
                reply = request(50052, 'flight.land', payload, timeout=min(8, max(.1, deadline-time.monotonic())))
                if reply.get('status') != 'ok':raise RuntimeError(str(reply.get('error')))
            except TimeoutError:
                # A lost/late ACK does not mean land_async was never started.
                # Observe completion instead of killing a descending vehicle.
                report(payload['device_id']+' 降落确认较慢，继续等待状态。')
        while time.monotonic() < deadline:
            try:
                reply = request(50052, 'sim.get_state', timeout=min(2, max(.1, deadline-time.monotonic())))
                if reply.get('status') != 'ok':raise RuntimeError(str(reply.get('error')))
                flight = reply['payload']
            except (OSError, ValueError, RuntimeError, KeyError):
                time.sleep(.25);continue
            if flight.get('run_id') != run_id:
                report('会话已改变，停止等待降落。');return False
            if all(i.get('flight_status') == 'ready' for i in (flight.get('fleet') or [flight])):
                report('无人机已降落，正在关闭仿真。'); return True
            time.sleep(.25)
        report('降落等待超时，将关闭本次仿真进程。')
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        report('仿真已退出或无法响应，将清理本次进程：' + str(error))
    return False
