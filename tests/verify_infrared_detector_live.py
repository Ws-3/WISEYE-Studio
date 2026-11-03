"""Fixed city P0/P1 benchmark. No flight or Fleet changes; restores runtime controls.

Repeatable configuration and seeded detector noise do not make UE cloud rendering
bitwise deterministic. Image statistics are engineering checks, not realism scores.
"""
import argparse,base64,hashlib,json,socket,time,subprocess
from pathlib import Path
import cv2
import numpy as np
from core.infrared_presets import DETECTOR_FIELDS


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,default=Path('configs/infrared_benchmark.json'))
    parser.add_argument('--replay',type=Path,required=True,help='Built tests/native/replay_thermal.cpp executable')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    raw=args.manifest.read_bytes();manifest=json.loads(raw);device=manifest['device']
    def rpc(command,payload=None,ok=True,ident=device):
        with socket.create_connection(('127.0.0.1',50051),5) as s:
            s.settimeout(20);s.sendall((json.dumps(dict(version=1,request_id=str(time.time_ns()),command=command,payload=dict(device_id=ident,**(payload or {}))))+'\n').encode())
            r=json.loads(s.makefile('rb').readline(20*1024**2))
        assert r['status']==('ok' if ok else 'error'),r
        return r['payload'] if ok else r
    def state():return rpc('sim.get_state')
    original=state();env=original['environment'];assert original['scene_id']==manifest['scene']
    assert original['sensors']['infrared']['detector_controls_available']
    keys=('enabled','fov_deg','palette','noise','thermal_profile','blur_px','contrast','background_detail','agc_enabled','agc_response_s','sampling_scale',*DETECTOR_FIELDS)
    initial={k:original['sensors']['infrared'][k] for k in keys}
    other_id=next((d['id'] for d in original.get('devices',[]) if d['kind']=='gimbal' and d['id']!=device),None)
    other=rpc('sim.get_state',ident=other_id)['sensors']['infrared'] if other_id else None
    report=dict(passed=False,run_id=original['run_id'],manifest=manifest,manifest_sha256=hashlib.sha256(raw).hexdigest(),captures={},checks={},performance={})
    images={}
    def configure(**changes):
        p={**initial,'enabled':True,'thermal_profile':'facade','sampling_scale':1,'noise':0,'noise_seed':manifest['noise_seed'],**changes}
        p['agc_enabled']=p['gain_mode']=='auto'
        return rpc('sensor.configure',dict(sensor='infrared',**p))
    def capture(name,count=6):
        time.sleep(1);frames=[];sequences=[];times=[];stats=[];last=-1;until=time.monotonic()+15
        while len(frames)<count and time.monotonic()<until:
            p=rpc('camera.stream_frame',dict(channel='CH2'))
            if p['frame_number']==last:time.sleep(.04);continue
            last=p['frame_number'];im=cv2.imdecode(np.frombuffer(base64.b64decode(p['image_base64']),np.uint8),1)
            assert im.shape==(512,640,3) and np.ptp(im,axis=2).max()<=2
            frames.append(im);sequences.append(last);times.append(p['simulation_time_s']);stats.append(state()['sensors']['infrared'])
        assert len(frames)==count,'No fresh sequence of frames'
        image=frames[-1];cv2.imencode('.png',image)[1].tofile(str(args.output/(name+'.png')));images[name]=image
        rough=[float(np.abs(cv2.Laplacian(f[20:230,20:300,0].astype(np.float32),cv2.CV_32F)).mean()) for f in frames]
        report['captures'][name]=dict(frame_numbers=sequences,simulation_times=times,sky_roughness_median=float(np.median(rough)),sensor=stats[-1],
            readout_ms_median=float(np.median([s['readout_ms'] for s in stats])))
        print('CAPTURE',name,'roughness',report['captures'][name]['sky_roughness_median'],flush=True)
        return image
    def performance(name):
        before=state();start=time.monotonic();samples=[]
        while time.monotonic()-start<6:
            s=state();samples.append((s['streams']['CH2']['cache_age_ms'],s['sensors']['infrared']['readout_ms']));time.sleep(.15)
        after=state();elapsed=time.monotonic()-start;data=np.array(samples)
        report['performance'][name]=dict(tick_hz=(after['tick_seq']-before['tick_seq'])/elapsed,
            ir_hz=(after['streams']['CH2']['completed_frames']-before['streams']['CH2']['completed_frames'])/elapsed,
            cache_age_ms_p50=float(np.percentile(data[:,0],50)),cache_age_ms_p95=float(np.percentile(data[:,0],95)),
            readout_ms_p50=float(np.percentile(data[:,1],50)))
    try:
        for case in manifest['cases']:
            rpc('environment.configure',dict(**manifest['conditions'],clouds=case['clouds']))
            if case.get('tracking'):rpc('gimbal.set_tracking',dict(enabled=True))
            else:rpc('gimbal.set_angles',{k:case[k] for k in ('yaw_deg','pitch_deg')})
            previous=state();stable=0;until=time.monotonic()+15
            while time.monotonic()<until:
                time.sleep(.3);current=state()
                delta=max(abs(current['yaw_deg']-previous['yaw_deg']),abs(current['pitch_deg']-previous['pitch_deg']))
                stable=stable+1 if delta<.02 else 0;previous=current
                if stable>=3:break
            assert stable>=3,'Camera did not settle before the fixed-view comparison'
            configure(fov_deg=case['fov_deg'],gain_mode='manual',manual_low=.05,manual_high=.45,brightness=0,blur_px=.8,contrast=1.1,sky_denoise=0,stable_agc=False)
            capture(case['id']+'_baseline')
            if case['id']=='cloud':performance('cloud_baseline_1x')
            rpc('camera.signal_recording',dict(enabled=True));time.sleep(.6)
            packet=rpc('camera.signal_frame');prefix=args.output/case['id']
            arrays={}
            for field,suffix,dtype in [('signal_base64','.f32','<f4'),('sky_mask_base64','.sky.u8','u1'),('target_mask_base64','.target.u8','u1')]:
                data=base64.b64decode(packet.pop(field));Path(str(prefix)+suffix).write_bytes(data)
                arrays[suffix]=np.frombuffer(data,dtype=dtype).reshape(512,640)
            assert np.isfinite(arrays['.f32']).all()
            assert not np.logical_and(arrays['.sky.u8'],arrays['.target.u8']).any()
            Path(str(prefix)+'.raw.json').write_text(json.dumps(packet,indent=2),encoding='utf8')
            rpc('camera.signal_recording',dict(enabled=False))
            outputs=[]
            for amount,label in [(0,'raw_baseline'),(.8,'raw_smooth')]:
                out=Path(str(prefix)+'_'+label+'.pgm')
                subprocess.run([str(args.replay),str(prefix)+'.f32',str(prefix)+'.sky.u8',str(prefix)+'.target.u8',str(out),str(amount)],check=True)
                outputs.append(cv2.imread(str(out),0))
            roi=np.zeros((512,640),np.uint8);roi[20:230,20:300]=1
            mask=cv2.erode(arrays['.sky.u8'].astype(np.uint8),np.ones((9,9),np.uint8)).astype(bool)&roi.astype(bool)
            if case['id']=='cloud':
                assert mask.sum()>10000
                rough=[float(np.abs(cv2.Laplacian(x.astype(np.float32),cv2.CV_32F))[mask].mean()) for x in outputs]
                report['checks']['same_input_cloud_roughness']=rough
                report['checks']['same_input_cloud_ratio']=rough[1]/max(.001,rough[0])
                assert rough[1]<rough[0]*.95,rough
                again=Path(str(prefix)+'_repeat.pgm')
                cmd=[str(args.replay),str(prefix)+'.f32',str(prefix)+'.sky.u8',str(prefix)+'.target.u8',str(again),'.8']
                subprocess.run(cmd,check=True)
                assert again.read_bytes()==Path(str(prefix)+'_raw_smooth.pgm').read_bytes()
                report['checks']['same_input_replay_identical']=True
            report['performance'][case['id']]=dict(baseline_readout_ms=report['captures'][case['id']+'_baseline']['readout_ms_median'])
            configure(fov_deg=case['fov_deg'],gain_mode='manual',manual_low=.05,manual_high=.45,brightness=0,blur_px=.8,contrast=1.1,sky_denoise=.8,stable_agc=False)
            capture(case['id']+'_smooth')
            if case['id']=='cloud':performance('cloud_smooth_1x')
        a=report['captures']['cloud_baseline'];b=report['captures']['cloud_smooth']
        assert b['sensor']['sky_pixels']>10000,'New sky mask did not reach the detector'
        ratio=b['sky_roughness_median']/max(.001,a['sky_roughness_median']);report['checks']['sequential_live_cloud_ratio_observational_only']=ratio
        assert b['sensor']['target_pixels']<1000,'Sky regressed to a thermal target'
        configure(sampling_scale=2,sky_denoise=.8,gain_mode='manual',manual_low=.05,manual_high=.45)
        capture('sampling_2x',3)
        rpc('camera.signal_recording',dict(enabled=True));time.sleep(.6)
        packet=rpc('camera.signal_frame')
        sky=np.frombuffer(base64.b64decode(packet['sky_mask_base64']),np.uint8)
        target=np.frombuffer(base64.b64decode(packet['target_mask_base64']),np.uint8)
        assert len(sky)==len(target)==640*512 and not np.logical_and(sky,target).any()
        report['checks']['sampling_2x_masks_disjoint']=True
        rpc('camera.signal_recording',dict(enabled=False))
        rpc('camera.signal_frame',ok=False)
        report['checks']['recording_off_rejects_frame']=True
        configure(sampling_scale=1)
        # Locked exposure must survive an entirely different field of view and a stop/resume.
        configure(gain_mode='auto',stable_agc=True,sky_denoise=.8);time.sleep(2)
        configure(gain_mode='locked');time.sleep(.4);locked=state()['sensors']['infrared']
        values=[]
        for yaw,pitch in ((0,12),(-15,65),(25,5)):
            rpc('gimbal.set_angles',dict(yaw_deg=yaw,pitch_deg=pitch));time.sleep(.5)
            values.append(state()['sensors']['infrared'])
        rpc('sensor.set_enabled',dict(sensor='infrared',enabled=False));time.sleep(.2)
        rpc('sensor.set_enabled',dict(sensor='infrared',enabled=True));time.sleep(.6);values.append(state()['sensors']['infrared'])
        assert all(abs(s['agc_low']-locked['agc_low'])<1e-6 and abs(s['agc_high']-locked['agc_high'])<1e-6 for s in values)
        report['checks']['locked_range']=[locked['agc_low'],locked['agc_high']]
        configure(gain_mode='manual',manual_low=.1,manual_high=.5,brightness=0);base=capture('manual_base',3)
        actual=state()['sensors']['infrared'];assert abs(actual['agc_low']-.1)<1e-6 and abs(actual['agc_high']-.5)<1e-6
        configure(gain_mode='manual',manual_low=.1,manual_high=.5,brightness=.1);bright=capture('manual_brighter',3)
        assert bright.mean()>base.mean()+2
        before={k:state()['sensors']['infrared'][k] for k in keys}
        for changes in [dict(manual_low=.5,manual_high=.4),dict(manual_low=.1,manual_high=.101),dict(noise_seed=1.5),dict(sky_denoise=True),dict(brightness=1),dict(gain_mode='invalid'),dict(stable_agc='true'),dict(gain_mode='locked',agc_enabled=True)]:
            rpc('sensor.configure',dict(sensor='infrared',**{**before,**changes}),ok=False)
            assert {k:state()['sensors']['infrared'][k] for k in keys}==before
        report['checks']['invalid_requests']=8
        if other_id:
            after=rpc('sim.get_state',ident=other_id)['sensors']['infrared']
            assert {k:after[k] for k in keys}=={k:other[k] for k in keys},'Another device changed'
        report['checks']['other_device_isolation']='passed' if other_id else 'not applicable: one gimbal'
        report['passed']=True
    finally:
        rpc('camera.signal_recording',dict(enabled=False))
        rpc('sensor.configure',dict(sensor='infrared',**initial))
        rpc('environment.configure',{k:env[k] for k in ('time_override','hour','fog','rain','clouds')})
        rpc('gimbal.set_angles',dict(yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']))
        rpc('gimbal.set_tracking',dict(enabled=original['tracking']))
        report['restored']=True
        (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('DETECTOR_ACCEPTANCE_PASSED',flush=True)


if __name__=='__main__':main()
