"""Real city material/target acceptance. Use an isolated data directory.

--flight temporarily switches the landed drone to Avata, takes off, lands,
waits for zero RPM, and restores its model. No fleet file is written.
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
    parser.add_argument('--device',default='ptz-02')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--flight',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)

    def rpc(command,payload=None,port=50051):
        payload={'device_id':args.device,**(payload or {})} if port==50051 else payload or {}
        with socket.create_connection(('127.0.0.1',port),5) as s:
            s.settimeout(15)
            s.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,payload=payload))+'\n').encode())
            result=json.loads(s.makefile('rb').readline(16*1024**2))
        assert result['status']=='ok',result
        return result['payload']

    def state():return rpc('sim.get_state')
    original=state();drone=original['tracking_target']
    original_drone=rpc('sim.get_state',{'device_id':drone})
    keys=('enabled','fov_deg','palette','noise','thermal_profile','blur_px','contrast','background_detail','agc_enabled','agc_response_s','sampling_scale')
    initial={k:original['sensors']['infrared'][k] for k in keys}
    assert original['sensors']['infrared'].get('classified_available')
    env=original['environment'];airborne=False
    report=dict(passed=False,run_id=original['run_id'],device=args.device,captures={},performance={},limits='Short editor test; label counts are pixel coverage, not classification accuracy; component name rules, not measured materials; selected Avata motor spots are projection proxies.')

    def configure(profile='classified',**changes):
        values={**initial,'enabled':True,'thermal_profile':profile,'noise':0,'palette':'white_hot','sampling_scale':1,**changes}
        rpc('sensor.configure',{'sensor':'infrared',**values})

    def wait_for(predicate,timeout=60):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return
            time.sleep(.2)
        raise TimeoutError('Runtime condition timed out')

    def frame():
        packet=rpc('camera.stream_frame',dict(channel='CH2'))
        image=cv2.imdecode(np.frombuffer(base64.b64decode(packet['image_base64']),np.uint8),cv2.IMREAD_COLOR)
        return image,packet

    def capture(name):
        time.sleep(3)
        _,before=frame();wait_for(lambda:frame()[1]['frame_number']>=before['frame_number']+3,20)
        image,packet=frame();actual=state()
        assert image.shape==(512,640,3) and image.std()>2
        assert np.ptp(image,axis=2).max()<=2
        cv2.imencode('.png',image)[1].tofile(str(args.output/(name+'.png')))
        report['captures'][name]=dict(frame=packet['frame_number'],sensor=actual['sensors']['infrared'],environment=actual['environment'],thermal_target=actual['thermal_target'])
        print('CAPTURE',name,actual['sensors']['infrared']['class_pixels'],flush=True)
        return image

    def environment(hour):rpc('environment.configure',dict(time_override=True,hour=hour,fog=env['fog'],rain=env['rain']))

    def performance(name):
        before=state();start=time.monotonic();samples=[]
        while time.monotonic()-start<8:
            s=state();samples.append((s['streams']['CH2']['cache_age_ms'],s['sensors']['infrared']['readout_ms']));time.sleep(.15)
        after=state();elapsed=time.monotonic()-start
        report['performance'][name]=dict(tick_hz=(after['tick_seq']-before['tick_seq'])/elapsed,
            ir_hz=(after['streams']['CH2']['completed_frames']-before['streams']['CH2']['completed_frames'])/elapsed,
            cache_age_ms_p50=float(np.percentile(np.array(samples)[:,0],50)),cache_age_ms_p95=float(np.percentile(np.array(samples)[:,0],95)),
            readout_ms_p50=float(np.percentile(np.array(samples)[:,1],50)))
        print(name,report['performance'][name],flush=True)

    def air(command='sim.get_state'):return rpc(command,dict(device_id=drone),50052)

    try:
        rpc('gimbal.set_tracking',dict(enabled=True));environment(12)
        configure('reference',fov_deg=25)
        reference=capture('reference_day');performance('reference_1x')
        configure(fov_deg=25)
        day=capture('materials_day');performance('materials_1x')
        counts=report['captures']['materials_day']['sensor']['class_pixels']
        assert len(counts)==7 and sum(counts)==640*512,counts
        assert sum(counts[1:])>1000,'No meaningful material labels reached the GPU'
        assert sum(c>10 for c in counts[1:])>=2,'Need more than one visible material category'
        environment(0);night=capture('materials_night')
        report['day_night_mean_difference']=float(np.abs(day.astype(float)-night.astype(float)).mean())
        assert report['day_night_mean_difference']>2,'Day/night preset did not change the IR image'
        configure(palette='black_hot',fov_deg=25)
        black=capture('materials_night_black')
        report['polarity_error']=float(np.abs(black.astype(float)+night.astype(float)-255).mean())
        assert report['polarity_error']<12
        configure(palette='white_hot',fov_deg=25)
        environment(12)
        if args.flight:
            assert air()['flight_status']=='ready'
            rpc('drone.set_model',dict(device_id=drone,model='avata'))
            configure(fov_deg=5)
            cold=capture('avata_cold')
            cold_state=rpc('sim.get_state',dict(device_id=drone))
            air('flight.takeoff');airborne=True
            wait_for(lambda:not air()['command_active'])
            time.sleep(15)
            hover=capture('avata_hover_warm')
            warm_state=rpc('sim.get_state',dict(device_id=drone))
            assert warm_state['rotor_telemetry_fresh'] and min(warm_state['motor_rpm'])>1000
            assert warm_state['thermal_target']['motor_warmth']>cold_state['thermal_target']['motor_warmth']+.002
            assert state()['sensors']['infrared']['target_pixels']>0
            assert state()['sensors']['infrared']['motor_region_pixels']>0,'Projected motor mask did not reach visible Avata body pixels'
            air('flight.land');wait_for(lambda:air()['flight_status']=='ready' and max(air()['motor_rpm'])<1);airborne=False
            wait_for(lambda:max(rpc('sim.get_state',dict(device_id=drone))['motor_rpm'])<1)
            capture('avata_landed_warm')
            landed=rpc('sim.get_state',dict(device_id=drone))['thermal_target']
            time.sleep(10);cooling=rpc('sim.get_state',dict(device_id=drone))['thermal_target']
            assert cooling['motor_warmth']<landed['motor_warmth']
            report['avata_flight']=dict(cold=cold_state['thermal_target'],hover=warm_state['thermal_target'],landed=landed,cooling=cooling,rpm=warm_state['motor_rpm'])
        tiles=[]
        for name,img in [('REFERENCE',reference),('MATERIALS / DAY',day),('MATERIALS / NIGHT',night)]:
            tile=cv2.copyMakeBorder(img,36,0,0,0,cv2.BORDER_CONSTANT,value=(25,25,25))
            cv2.putText(tile,name,(12,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(230,230,230),1,cv2.LINE_AA);tiles.append(tile)
        cv2.imencode('.png',np.hstack(tiles))[1].tofile(str(args.output/'comparison.png'))
        report['passed']=True
    finally:
        try:
            if airborne:
                air('flight.land');wait_for(lambda:air()['flight_status']=='ready' and max(air()['motor_rpm'])<1)
            rpc('drone.set_model',dict(device_id=drone,model=original_drone['drone_model']))
            rpc('sensor.configure',dict(sensor='infrared',**initial))
            rpc('environment.configure',{k:env[k] for k in ('time_override','hour','fog','rain')})
            rpc('gimbal.set_angles',dict(yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']))
            rpc('gimbal.set_tracking',dict(enabled=original['tracking']))
            report['restored']=True
        finally:
            (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(passed=report['passed'],output=str(args.output))),flush=True)


if __name__=='__main__':main()
