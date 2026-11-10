"""Owned Small City imaging captures with takeoff/hover/landing; isolated config."""
import argparse
import base64
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from core.local_rpc import request
from core.process_job import ProcessJob


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--visible-probe',action='store_true')
    parser.add_argument('--sensor-upgrade',action='store_true')
    parser.add_argument('--vehicle-probe',action='store_true')
    parser.add_argument('--engine-root',type=Path)
    parser.add_argument('--project',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    def local_path(override,name,fallback):
        if override:return override.resolve()
        setting=root/'scripts'/name
        path=Path(setting.read_text(encoding='utf-8-sig').strip()) if setting.exists() else fallback
        return path if path.is_absolute() else root/path
    engine=local_path(args.engine_root,'engine-root.local.txt',Path('Tools/UE_5.8'))
    project=local_path(args.project,'preview-project.local.txt',Path('ue5/WISEYE/test.uproject'))
    editor=engine/'Engine/Binaries/Win64/UnrealEditor.exe'
    assert editor.is_file() and project.is_file(),'Set --engine-root/--project to the actual local preview'
    data=root/'builds/imaging-realism-test-data'
    out=root/'builds/imaging-realism'/args.tag
    out.mkdir(parents=True,exist_ok=True)
    for folder in ['configs','ue5/WISEYE/Config/WISEYE']:
        shutil.copytree(root/folder,data/folder,dirs_exist_ok=True)
    scene=json.loads((data/'ue5/WISEYE/Config/WISEYE/Scenes/city.json').read_text(encoding='utf-8-sig'))
    try:
        request(50051,'sim.ping')
    except OSError:
        pass
    else:
        raise RuntimeError('Port is occupied; do not share another simulation')
    env=dict(os.environ,WISEYE_DATA_DIR=str(data),WISEYE_RESOURCES_DIR=str(root),PYTHONUTF8='1')
    job=ProcessJob();report={'tag':args.tag,'captures':{},'flight_performed':False};airborne=False
    vehicle_tracker=None
    def rpc(command,port=50051,**values):
        r=request(port,command,values,timeout=12)
        if r['status']!='ok':raise ValueError(r)
        return r['payload']
    def wait(function,seconds):
        end=time.monotonic()+seconds;last=None
        while time.monotonic()<end:
            if game.poll() is not None:raise RuntimeError('Owned UE exited')
            try:
                result=function()
                if result:return result
            except (OSError,ValueError,KeyError) as error:last=str(error)
            time.sleep(.2)
        raise TimeoutError(last or 'Capture readiness timed out')
    def frame(device,channel):return rpc('camera.stream_frame',device_id=device,channel=channel)
    def capture(name,device,channel):
        # Exercise demand-driven cameras; give exposure a fixed warm-up interval.
        end=time.monotonic()+5
        while time.monotonic()<end:
            if vehicle_tracker and name.startswith('parked-vehicle'):vehicle_tracker()
            wait(lambda:frame(device,channel),35);time.sleep(.1)
        packet=frame(device,channel)
        (out/(name+'.jpg')).write_bytes(base64.b64decode(packet.pop('image_base64')))
        report['captures'][name]=packet
        if channel=='AERIAL_IR':
            from io import BytesIO
            import numpy as np
            from PIL import Image
            rows=[]
            for _ in range(8):
                time.sleep(.18);sample=frame(device,channel)
                pixels=np.asarray(Image.open(BytesIO(base64.b64decode(sample['image_base64']))).convert('L'))[120:180,330:390]
                rows.append(dict(frame=sample['frame_number'],median_dn=float(np.median(pixels)),std_dn=float(pixels.std())))
            assert len({r['frame'] for r in rows})>=6,rows
            report.setdefault('temporal_road_roi',{})[name]=rows
            current=rpc('sim.get_state')
            report.setdefault('aerial_readouts',{})[name]=next(d['aerial']['infrared'] for d in current['devices'] if d['id']==device)
        print('CAPTURE',name,flush=True)
    try:
        with (out/'ue-stdout.log').open('wb') as log:
            startup=None
            if args.sensor_upgrade:
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
            extra=['-WiseEyeHiddenWindow','-WinX=-32000','-WinY=-32000','-ExecCmds=t.IdleWhenNotForeground 0'] if args.sensor_upgrade else []
            game=job.spawn([str(editor),str(project),scene['map']+'?game=/Script/test.WiseEyeGameMode?wiseeye_scene=city',
                '-game','-windowed','-ResX=1280','-ResY=720','-nosplash',
                '-WiseEyeDataDir='+str(data),'-UserDir='+str(data/'UE'),'-simlogdir='+str(out)]+extra,
                cwd=root,env=env,stdout=log,stderr=log,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
        state=wait(lambda:rpc('sim.get_state'),600);report['run_id']=state['run_id']
        wait(lambda:len(rpc('sim.get_state').get('devices',[]))>=2,180)
        if args.sensor_upgrade:
            assert not rpc('sim.get_state')['ue_window_visible']
            assert rpc('sim.window.set_visible',visible=True)['ue_window_visible']
            time.sleep(.5)
            assert not rpc('sim.window.set_visible',visible=False)['ue_window_visible']
            report['window_control']=dict(started_hidden=True,shown=True,hidden_again=True)
        if args.visible_probe:
            rpc('gimbal.set_tracking',device_id='ptz-01',enabled=False)
            rpc('gimbal.set_angles',device_id='ptz-01',yaw_deg=0,pitch_deg=12)
            rpc('environment.configure',time_override=True,hour=12,fog=0,rain=0,clouds=0)
            for name,blur,noise,contrast,saturation in [('neutral',0,0,1,1),('blur-only',.55,0,1,1),
                ('tone-only',0,0,.96,.88),('noise-only',0,.006,1,1),('default',.55,.006,.96,.88)]:
                rpc('sensor.configure',device_id='ptz-01',sensor='visible',enabled=True,fov_deg=25,
                    blur_px=blur,noise=noise,contrast=contrast,saturation=saturation)
                capture(name,'ptz-01','CH1')
            report['passed']=True
            return
        with (out/'flight.log').open('wb') as log:
            worker=job.spawn([sys.executable,'-m','integrations.ProjectAirSim.run_wiseye_flight','--scene','city','--loops','0'],
                cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        wait(lambda:rpc('sim.get_state',50052),180)
        def flight():return rpc('sim.get_state',50052,device_id='uav-01')
        def drone():return next(d for d in rpc('sim.get_state')['devices'] if d['id']=='uav-01')
        start_z=drone()['position_cm'][2]
        rpc('flight.takeoff',50052,device_id='uav-01');airborne=True
        wait(lambda:not flight()['command_active'],90)
        rpc('flight.set_mode',50052,device_id='uav-01',mode='manual')
        target_z=start_z+2000
        end=time.monotonic()+45
        while drone()['position_cm'][2]<target_z-10:
            if time.monotonic()>end:raise TimeoutError('Imaging altitude not reached')
            up=min(1,max(.15,(target_z-drone()['position_cm'][2])/300))
            rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=up,yaw=0)
            time.sleep(.1)
        rpc('flight.set_input',50052,device_id='uav-01',forward=0,right=0,up=0,yaw=0)
        rpc('flight.hover',50052,device_id='uav-01')
        wait(lambda:not flight()['command_active'],30)
        report['flight_performed']=True;report['hover_position_cm']=drone()['position_cm']
        rpc('gimbal.set_tracking',device_id='ptz-01',enabled=False)
        rpc('gimbal.set_angles',device_id='ptz-01',yaw_deg=0,pitch_deg=12)
        aerial=next(d['aerial'] for d in rpc('sim.get_state')['devices'] if d['id']=='uav-01')
        rpc('aerial.configure',**dict(aerial,device_id='uav-01',enabled=True,ir_enabled=True,
            stabilized=True,pitch_deg=-55,yaw_deg=-25,fov_deg=65,ir_fov_deg=65,
            sample_hz=15,ir_sample_hz=15,ir_noise=.008,ir_blur_px=.8,ir_black_hot=False))
        if args.vehicle_probe:
            rpc('environment.configure',time_override=True,hour=12,fog=0,rain=0,clouds=0)
            origin=wait(lambda:frame('uav-01','AERIAL'),40)['camera_position_cm']
            def car_samples():
                frame('uav-01','AERIAL') # keep the LOS source camera allocated
                data=rpc('population.get_agents',from_camera='uav-01')
                rows=data.get('parked_vehicle',{}).get('samples',[]) or data.get('vehicle',{}).get('samples',[])
                rows=data.get('parked_vehicle',{}).get('samples',[])+data.get('vehicle',{}).get('samples',[])
                close=[v for v in rows if math.dist(v['position_cm'],origin)<15000]
                return close or rows
            vehicles=wait(car_samples,180)
            preferred=[v for v in vehicles if v.get('los_clear')]
            target=min(preferred or vehicles,key=lambda v:math.dist(v['position_cm'],origin))
            report['vehicle_candidates']=sorted(vehicles,key=lambda v:math.dist(v['position_cm'],origin))[:12]
            dx,dy,dz=[a-b for a,b in zip(target['position_cm'],origin)];dz+=100
            pitch=max(-90,min(20,math.degrees(math.atan2(dz,math.hypot(dx,dy)))))
            yaw=(math.degrees(math.atan2(dy,dx))-flight()['yaw_deg']+180)%360-180
            current=next(d['aerial'] for d in rpc('sim.get_state')['devices'] if d['id']=='uav-01')
            rpc('aerial.configure',**dict(current,device_id='uav-01',pitch_deg=pitch,yaw_deg=yaw,fov_deg=15,ir_fov_deg=15))
            last_follow=[0.]
            def follow_car():
                if time.monotonic()-last_follow[0]<.25:return
                last_follow[0]=time.monotonic()
                item=next((v for v in car_samples() if v['target_id']==target['target_id']),target)
                ax,ay,az=[a-b for a,b in zip(item['position_cm'],origin)];az+=100
                p=max(-90,min(20,math.degrees(math.atan2(az,math.hypot(ax,ay)))))
                y=(math.degrees(math.atan2(ay,ax))-flight()['yaw_deg']+180)%360-180
                rpc('aerial.configure',**dict(current,device_id='uav-01',pitch_deg=p,yaw_deg=y,fov_deg=15,ir_fov_deg=15))
            vehicle_tracker=follow_car
            capture('parked-vehicle-visible','uav-01','AERIAL');capture('parked-vehicle-ir','uav-01','AERIAL_IR')
            report['vehicle_probe']=target;report['annotation_status']='unavailable; target position is not a visible 2D ground-truth box'
            report['passed']=True
            return
        for period,hour in [('day',12),('night',0)]:
            rpc('environment.configure',time_override=True,hour=hour,fog=0,rain=0,clouds=0)
            for prefix,device,channel in [('aerial-visible','uav-01','AERIAL'),('aerial-ir','uav-01','AERIAL_IR'),
                ('gimbal-visible','ptz-01','CH1'),('gimbal-ir','ptz-01','CH2')]:
                capture(period+'-'+prefix,device,channel)
            report[period+'_state']=rpc('sim.get_state')
        if args.sensor_upgrade:
            import cv2
            import numpy as np
            from core.sensor_formats import pointcloud2,metavision_events
            rpc('environment.configure',time_override=True,hour=12,fog=0,rain=0,clouds=0)
            current=next(d['aerial'] for d in rpc('sim.get_state')['devices'] if d['id']=='uav-01')
            for name,blur in [('aerial-optics-neutral',0),('aerial-optics-soft',2.5)]:
                rpc('aerial.configure',**dict(current,device_id='uav-01',vis_blur_px=blur,focus_mode='off'))
                capture(name,'uav-01','AERIAL')
            def aerial_detail(name):
                image=cv2.imread(str(out/(name+'.jpg')),0)[200:800,50:700]
                return float(cv2.Laplacian(image,cv2.CV_64F).var())
            report['aerial_optics']=dict(neutral=aerial_detail('aerial-optics-neutral'),soft=aerial_detail('aerial-optics-soft'))
            assert report['aerial_optics']['soft']<report['aerial_optics']['neutral']*.85,report['aerial_optics']
            rpc('aerial.configure',**dict(current,device_id='uav-01',vis_blur_px=.95,focus_mode='auto'))
            def lens(mode,**values):return rpc('sensor.configure',device_id='ptz-01',sensor='visible',enabled=True,fov_deg=25,blur_px=.95,focus_mode=mode,**values)
            lens('off');capture('focus-off','ptz-01','CH1')
            lens('manual',focus_distance_m=.2,aperture_f=1);capture('focus-near','ptz-01','CH1')
            def sharp(name):
                image=cv2.imread(str(out/(name+'.jpg')),0)[760:1060,280:1540]
                return float(cv2.Laplacian(image,cv2.CV_64F).var())
            report['focus_render']=dict(off=sharp('focus-off'),defocused=sharp('focus-near'))
            assert report['focus_render']['defocused']<report['focus_render']['off']*.8,report['focus_render']
            original=rpc('sim.get_state',device_id='ptz-01')['sensors']['visible']
            invalid=request(50051,'sensor.configure',dict(device_id='ptz-01',sensor='visible',enabled=True,fov_deg=10,focus_mode='invalid'))
            assert invalid['status']=='error'
            assert rpc('sim.get_state',device_id='ptz-01')['sensors']['visible']['fov_deg']==original['fov_deg']
            lens('auto',aperture_f=2.8);rpc('gimbal.set_tracking',device_id='ptz-01',enabled=True);time.sleep(3)
            report['auto_focus']=rpc('sim.get_state',device_id='ptz-01')['sensors']['visible']
            assert report['auto_focus']['actual_focus_distance_m']>.2
            rpc('gimbal.set_tracking',device_id='ptz-01',enabled=False);rpc('gimbal.set_angles',device_id='ptz-01',yaw_deg=0,pitch_deg=-10)
            rpc('sensor.set_enabled',device_id='ptz-01',sensor='lidar',enabled=True);time.sleep(1)
            scan=rpc('sensor.lidar.get_scan',device_id='ptz-01');ros=pointcloud2(scan)
            assert not scan['lidar_downsampled'] and len(scan['lidar_ranges_m'])==scan['lidar_horizontal_samples']*scan['lidar_vertical_samples']
            assert ros['width']>0
            lengths=np.linalg.norm(np.asarray(scan['lidar_points_m']),axis=1)
            assert np.allclose(lengths,[v for v in scan['lidar_ranges_m'] if v>=0],rtol=.001,atol=.001)
            report['lidar']=dict(points=ros['width'],scan_sequence=scan['lidar_scan_sequence'],capture_time=scan['lidar_capture_time_s'])
            (out/'lidar-packet.json').write_text(json.dumps(scan,ensure_ascii=False,indent=2),encoding='utf-8')
            rpc('sensor.set_enabled',device_id='ptz-01',sensor='event',enabled=True);time.sleep(2)
            rpc('gimbal.set_angles',device_id='ptz-01',yaw_deg=8,pitch_deg=-5);time.sleep(2)
            events=rpc('sensor.event.get_packet',device_id='ptz-01',latest=True,max_events=4000);converted=metavision_events(events)
            assert len(converted)>0 and events['hardware_timing'] is False
            report['events']=dict(count=len(converted),actual_sample_hz=events['actual_sample_hz'],hardware_timing=events['hardware_timing'])
            (out/'event-packet.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf-8')
            np.save(out/'events-eventcd.npy',converted)
            assert not rpc('sim.get_state')['ue_window_visible']
        report['passed']=True
    finally:
        if airborne:
            try:
                rpc('flight.land',50052,device_id='uav-01')
                wait(lambda:rpc('sim.get_state',50052,device_id='uav-01')['flight_status']=='ready',100)
                report['landed']=True
            except Exception as error:report['landing_error']=str(error)
        job.close()
        if 'game' in locals():game.wait(timeout=30)
        report['owned_session_stopped']=True
        log_path=data/'UE/Saved/Logs/test.log'
        text=log_path.read_text(encoding='utf-8',errors='replace') if log_path.exists() else ''
        report['material_compile_errors']=[line for line in text.splitlines() if 'Failed to compile Material /Game/WISEYE/' in line]
        report['material_runtime_errors']=[line for line in text.splitlines() if 'is not a valid parent for MaterialInstanceDynamic' in line]
        if report['material_runtime_errors']:report['passed']=False
        if report['material_compile_errors']:report['passed']=False
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if report['material_compile_errors']:raise AssertionError(report['material_compile_errors'])
        if report['material_runtime_errors']:raise AssertionError(report['material_runtime_errors'])


if __name__=='__main__':main()
