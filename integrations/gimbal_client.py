"""Standard-library SDK for WISEYE gimbals over the existing JSON Lines API."""
import json
import math
import socket
import uuid


class GimbalError(RuntimeError):
    pass


class GimbalClient:
    def __init__(self, device_id='ptz-01', host='127.0.0.1', port=50051, timeout=2.0):
        self.device_id,self.host,self.port,self.timeout=device_id,host,port,timeout

    def request(self, command, **payload):
        request_id=uuid.uuid4().hex
        request=dict(version=1,request_id=request_id,command=command,
                     payload=dict(payload,device_id=self.device_id))
        with socket.create_connection((self.host,self.port),self.timeout) as connection:
            connection.sendall((json.dumps(request,allow_nan=False)+'\n').encode())
            with connection.makefile('rb') as stream:
                line=stream.readline(1024*1024+1)
        if not line.endswith(b'\n') or len(line)>1024*1024:raise GimbalError('Missing or oversized response')
        reply=json.loads(line)
        if reply.get('version')!=1 or reply.get('request_id')!=request_id:raise GimbalError('Response identity mismatch')
        if reply.get('status')!='ok':raise GimbalError(str(reply.get('error',reply)))
        return reply['payload']

    def capabilities(self):return self.request('gimbal.get_capabilities')['gimbal_capabilities']
    def state(self):return self.request('sim.get_state')
    def take_control(self):return self.request('input.set_mode',mode='gimbal')
    def set_angles(self, yaw_deg, pitch_deg):
        for value in (yaw_deg,pitch_deg):
            if type(value) not in (float,int) or not math.isfinite(value):raise ValueError('Angles must be finite numbers')
        return self.request('gimbal.set_angles',yaw_deg=yaw_deg,pitch_deg=pitch_deg)
    def set_velocity(self, yaw_deg_s=0.0, pitch_deg_s=0.0):
        for value,limit in ((yaw_deg_s,30),(pitch_deg_s,20)):
            if type(value) not in (float,int) or not math.isfinite(value) or abs(value)>limit:
                raise ValueError('Velocity exceeds capabilities (yaw ±30, pitch ±20 degree/s)')
        return self.request('gimbal.set_input',yaw=yaw_deg_s/30,pitch=pitch_deg_s/20)
    def stop(self):return self.set_velocity()
    def hold(self):
        self.stop()
        return self.request('gimbal.set_tracking',enabled=False)
    def track(self, drone_id):
        self.request('gimbal.set_target',drone_id=drone_id)
        return self.request('gimbal.set_tracking',enabled=True)

    def point_at_world(self,position_cm,sensor='visible',*,scene_id=None,run_id=None):
        """One-shot optical-axis aim; repeat with fresh coordinates to follow."""
        from core.georeference import vector
        position=vector(position_cm)
        if sensor not in ('visible','infrared'):raise ValueError('Sensor must be visible or infrared')
        state=self.state()
        if scene_id is not None and scene_id!=state['scene_id']:raise GimbalError('Scene identity mismatch')
        if run_id is not None and run_id!=state['run_id']:raise GimbalError('Run identity mismatch')
        return self.request('gimbal.point_at',position_cm=position,sensor=sensor,scene_id=state['scene_id'],run_id=state['run_id'])

    def point_at_geodetic(self,reference,latitude_deg,longitude_deg,ellipsoid_height_m,sensor='visible',*,run_id=None):
        """WGS84 ellipsoid height; reference is an explicitly configured anchor."""
        return self.point_at_world(reference.geodetic_to_world(latitude_deg,longitude_deg,ellipsoid_height_m),sensor,scene_id=reference.scene_id,run_id=run_id)

    def coordinates(self,reference=None):
        """Native device locations plus optional explicitly anchored simulation LLA."""
        state=self.state()
        if reference is not None and reference.scene_id!=state['scene_id']:raise GimbalError('Scene identity mismatch')
        devices=[]
        for device in state['devices']:
            item=dict(id=device['id'],kind=device['kind'],position_cm=list(device['position_cm']),position_m=[v/100 for v in device['position_cm']],geodetic=None)
            if reference is not None:
                lat,lon,h=reference.world_to_geodetic(device['position_cm'])
                item['geodetic']=dict(latitude_deg=lat,longitude_deg=lon,ellipsoid_height_m=h)
            devices.append(item)
        return dict(scene_id=state['scene_id'],run_id=state['run_id'],reference=reference.to_dict() if reference else None,devices=devices)
