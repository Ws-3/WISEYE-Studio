"""Progress watchdog. A connected socket or repeated video frame is not liveness."""
class SimulationHealth:
    def __init__(self, timeout=3.0):
        self.timeout=timeout
        self.key=None
        self.sequence=None
        self.advanced=None
        self.received=None
        self.render_stale=False

    def observe(self, state, now):
        key=(state.get('run_id'), state.get('gimbal_id'))
        sequence=state.get('tick_seq')
        if key!=self.key or sequence!=self.sequence:
            self.key,self.sequence,self.advanced=key,sequence,now
        self.received=now
        streams=state.get('streams',{})
        sensors=state.get('sensors',{})
        self.render_stale=any(sensors.get(sensor,{}).get('enabled',False) and
                              streams.get(channel,{}).get('cache_age_ms',0)>self.timeout*1000
                              for channel,sensor in [('CH1','visible'),('CH2','infrared')])

    def status(self, now, connected):
        if not connected:return False,'未连接 UE'
        if self.received is None:return False,'等待仿真状态'
        if now-self.received>self.timeout:return False,'UE 状态响应停滞；网络连接仍可能存在'
        if self.sequence is None:return False,'UE 版本缺少推进计数，请重新构建'
        if now-self.advanced>self.timeout:return False,'UE 仿真停止推进；连接仍在'
        if self.render_stale:return False,'UE 仍在推进，但传感器渲染停滞'
        return True,'UE 正在推进'
