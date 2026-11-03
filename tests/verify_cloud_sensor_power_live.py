"""Validate actual city clouds and per-device sensor stop/resume. No flight/Fleet writes."""
import argparse,base64,json,socket,time
from pathlib import Path
import cv2
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--power-only',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    def call(command,payload=None,device='ptz-02',ok=True):
        with socket.create_connection(('127.0.0.1',50051),5) as s:
            s.settimeout(20);s.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,payload=dict(device_id=device,**(payload or {}))))+'\n').encode())
            r=json.loads(s.makefile('rb').readline(20*1024**2))
        if ok:assert r['status']=='ok',r
        else:assert r['status']=='error',r
        return r['payload'] if ok else r
    def state(device='ptz-02'):return call('sim.get_state',device=device)
    original=state();env=original['environment'];assert original['sensor_power_supported'] and env['clouds_supported']
    irkeys=('enabled','fov_deg','palette','noise','thermal_profile','blur_px','contrast','background_detail','agc_enabled','agc_response_s','sampling_scale')
    ir={k:original['sensors']['infrared'][k] for k in irkeys}
    vis={k:original['sensors']['visible'][k] for k in ('enabled','fov_deg')}
    report=dict(passed=False,run_id=original['run_id'],checks=[],images={},limits='Cloud signal estimated from rendered daylight appearance, not physical cloud temperature; stopped channels retain small configuration/render target allocations; UE scene and other devices continue running.')
    def power(sensor,enabled):return call('sensor.set_enabled',dict(sensor=sensor,enabled=enabled))
    def environment(clouds):return call('environment.configure',dict(time_override=True,hour=12,fog=0,rain=0,clouds=clouds))
    def capture(name,channel):
        time.sleep(4)
        packet=call('camera.stream_frame',dict(channel=channel));im=cv2.imdecode(np.frombuffer(base64.b64decode(packet['image_base64']),np.uint8),cv2.IMREAD_COLOR)
        assert im is not None and im.std()>1
        cv2.imencode('.png',im)[1].tofile(str(args.output/(name+'.png')))
        report['images'][name]=dict(frame=packet['frame_number'],shape=list(im.shape))
        return im
    try:
        call('gimbal.set_angles',dict(yaw_deg=-15,pitch_deg=65))
        call('sensor.configure',dict(sensor='visible',enabled=True,fov_deg=80))
        call('sensor.configure',dict(sensor='infrared',**{**ir,'enabled':True,'fov_deg':80,'thermal_profile':'facade','noise':0,'background_detail':.8,'agc_response_s':.4,'sampling_scale':1}))
        if not args.power_only:
            environment(0);a=capture('clear_visible','CH1');b=capture('clear_infrared','CH2')
            environment(.75);c=capture('clouds_visible','CH1');d=capture('clouds_infrared','CH2')
            report['visible_cloud_difference']=float(np.abs(a.astype(float)-c.astype(float)).mean())
            report['infrared_cloud_difference']=float(np.abs(b.astype(float)-d.astype(float)).mean())
            assert report['visible_cloud_difference']>3,report['visible_cloud_difference']
            assert report['infrared_cloud_difference']>1,report['infrared_cloud_difference']
            sky=d[20:230,20:300,0]
            report['cloud_sky_gray_std']=float(sky.std())
            report['cloud_sky_gray_p95_p5']=float(np.percentile(sky,95)-np.percentile(sky,5))
            assert report['cloud_sky_gray_p95_p5']>4,'Sky changed uniformly without resolved cloud structure'
            report['sky_target_pixels']=state()['sensors']['infrared']['target_pixels']
            assert report['sky_target_pixels']<1000,'Far clear stencil was misread as a thermal target'
        # Reject malformed inputs without changing the environment or sensor power.
        for payload in [dict(sensor='infrared',enabled=1),dict(sensor='unknown',enabled=False)]:call('sensor.set_enabled',payload,ok=False)
        call('environment.configure',dict(time_override=True,hour=12,fog=0,rain=0,clouds=True),ok=False)
        if not args.power_only:assert abs(state()['environment']['clouds']-.75)<.01
        for enabled in ((True,False,False),(True,True,False),(False,True,False),(False,False,False)):
            for sensor,value in zip(('visible','infrared','lidar'),enabled):power(sensor,value)
            time.sleep(.8);before=state();other=state('ptz-01');time.sleep(2);after=state();other_after=state('ptz-01')
            for sensor,channel,value in [('visible','CH1',enabled[0]),('infrared','CH2',enabled[1])]:
                frames=after['streams'][channel]['completed_frames']-before['streams'][channel]['completed_frames']
                assert frames>0 if value else frames==0,(sensor,value,frames)
                captures=after['sensors'][sensor]['capture_sequence']-before['sensors'][sensor]['capture_sequence']
                assert captures>0 if value else captures==0,(sensor,value,captures)
                if not value:
                    error=call('camera.stream_frame',dict(channel=channel),ok=False)
                    assert error['error']['code']=='sensor_disabled'
            assert after['sensors']['lidar']['scan_sequence']==before['sensors']['lidar']['scan_sequence']
            assert other_after['streams']['CH1']['completed_frames']>other['streams']['CH1']['completed_frames'],'Another device was inadvertently stopped'
            report['checks'].append(dict(enabled=enabled,before=before['streams'],after=after['streams'],capture_sequences={s:after['sensors'][s]['capture_sequence'] for s in ('visible','infrared')},lidar_sequence=after['sensors']['lidar']['scan_sequence']))
            print('POWER',enabled,flush=True)
        for _ in range(3):power('infrared',True);power('infrared',False)
        power('infrared',True);power('visible',True);power('lidar',True)
        time.sleep(3);s=state();assert s['sensors']['lidar']['scan_sequence']>after['sensors']['lidar']['scan_sequence']
        capture('resumed_infrared','CH2')
        report['passed']=True
    finally:
        call('sensor.configure',dict(sensor='infrared',**ir));call('sensor.configure',dict(sensor='visible',**vis))
        power('lidar',original['sensors']['lidar']['enabled'])
        call('environment.configure',{k:env[k] for k in ('time_override','hour','fog','rain','clouds')})
        call('gimbal.set_angles',dict(yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']));call('gimbal.set_tracking',dict(enabled=original['tracking']))
        (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('CLOUD_POWER_ACCEPTANCE_PASSED',flush=True)


if __name__=='__main__':main()
