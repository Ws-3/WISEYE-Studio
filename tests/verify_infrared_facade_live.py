"""Same-pose city facade appearance comparison; requires an isolated running UE.

Does not write Fleet or fly a drone. Restores sensor, environment and gimbal state.
Pixel differences verify that the path works, not similarity to a real camera.
"""
import argparse
import base64
import json
from pathlib import Path
import socket
import time

import cv2
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--device',default='ptz-02')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)

    def rpc(command,payload=None):
        with socket.create_connection(('127.0.0.1',50051),5) as s:
            s.settimeout(20)
            s.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,
                payload=dict(device_id=args.device,**(payload or {}))))+'\n').encode())
            r=json.loads(s.makefile('rb').readline(20*1024**2))
        assert r['status']=='ok',r
        return r['payload']

    original=rpc('sim.get_state');env=original['environment']
    keys=('enabled','fov_deg','palette','noise','thermal_profile','blur_px','contrast','background_detail','agc_enabled','agc_response_s','sampling_scale')
    initial={k:original['sensors']['infrared'][k] for k in keys}
    visible={k:original['sensors']['visible'][k] for k in ('enabled','fov_deg')}
    assert original['sensors']['infrared']['facade_available']
    report=dict(passed=False,run_id=original['run_id'],device=args.device,captures={},performance={},
        limitations='Material and geometry cues are appearance proxies, not measured temperatures or LWIR glass optics. Pixel differences are not realism scores.')
    images={}

    def configure(profile,**values):
        rpc('sensor.configure',dict(sensor='infrared',**{**initial,'enabled':True,'fov_deg':50,
            'thermal_profile':profile,'palette':'white_hot','noise':0,'blur_px':.8,'contrast':1.15,
            'background_detail':.8,'agc_enabled':True,'agc_response_s':.4,'sampling_scale':1,**values}))

    def capture(name,channel='CH2'):
        time.sleep(3)
        packet=rpc('camera.stream_frame',dict(channel=channel))
        image=cv2.imdecode(np.frombuffer(base64.b64decode(packet['image_base64']),np.uint8),cv2.IMREAD_COLOR)
        assert image is not None and image.std()>2
        if channel=='CH2':
            assert image.shape==(512,640,3)
            assert np.ptp(image,axis=2).max()<=2
        cv2.imencode('.png',image)[1].tofile(str(args.output/(name+'.png')))
        state=rpc('sim.get_state')
        report['captures'][name]=dict(frame=packet['frame_number'],sensor=state['sensors']['infrared'],
            yaw_deg=state['yaw_deg'],pitch_deg=state['pitch_deg'])
        images[name]=image
        print('CAPTURE',name,flush=True)
        return image

    def performance(name):
        before=rpc('sim.get_state');start=time.monotonic();samples=[]
        while time.monotonic()-start<8:
            s=rpc('sim.get_state');samples.append((s['streams']['CH2']['cache_age_ms'],s['sensors']['infrared']['readout_ms']));time.sleep(.15)
        after=rpc('sim.get_state');elapsed=time.monotonic()-start
        report['performance'][name]=dict(tick_hz=(after['tick_seq']-before['tick_seq'])/elapsed,
            ir_hz=(after['streams']['CH2']['completed_frames']-before['streams']['CH2']['completed_frames'])/elapsed,
            cache_age_ms_p50=float(np.percentile(np.array(samples)[:,0],50)),cache_age_ms_p95=float(np.percentile(np.array(samples)[:,0],95)),
            readout_ms_p50=float(np.percentile(np.array(samples)[:,1],50)))

    try:
        rpc('environment.configure',dict(time_override=True,hour=12,fog=0,rain=0))
        rpc('sensor.configure',dict(sensor='visible',enabled=True,fov_deg=50))
        for view,yaw,pitch in (('street',0,12),('upper',-15,28)):
            rpc('gimbal.set_angles',dict(yaw_deg=yaw,pitch_deg=pitch))
            capture(view+'_visible','CH1')
            configure('classified');old=capture(view+'_classified')
            if view=='street':performance('classified_1x')
            configure('facade');new=capture(view+'_facade')
            if view=='street':performance('facade_1x')
            delta=float(np.abs(new.astype(float)-old.astype(float)).mean())
            assert delta>2,'Facade path did not visibly change the city'
            report[view+'_mean_difference']=delta
            counts=report['captures'][view+'_facade']['sensor']['class_pixels']
            assert len(counts)==7 and sum(counts)==640*512 and counts[2]>1000
        configure('facade',palette='black_hot');black=capture('upper_black')
        error=float(np.abs(black.astype(float)+images['upper_facade'].astype(float)-255).mean())
        assert error<8,error
        report['polarity_error']=error
        configure('facade',background_detail=0);flat=capture('upper_detail_zero')
        assert np.abs(flat.astype(float)-images['upper_facade'].astype(float)).mean()>1
        for mode in ('reference','enhanced','legacy'):
            configure(mode);capture('compat_'+mode)
        report['passed']=True
    finally:
        rpc('sensor.configure',dict(sensor='infrared',**initial))
        rpc('sensor.configure',dict(sensor='visible',**visible))
        rpc('environment.configure',dict(time_override=env['time_override'],hour=env['hour'],fog=env['fog'],rain=env['rain']))
        rpc('gimbal.set_angles',dict(yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']))
        rpc('gimbal.set_tracking',dict(enabled=original['tracking']))
        (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('FACADE_ACCEPTANCE_PASSED',flush=True)


if __name__=='__main__':main()
