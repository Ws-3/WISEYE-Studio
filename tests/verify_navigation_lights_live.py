"""Exercise both model lamps in an owned live city; restore and land on exit."""
import argparse
import base64
import json
import io
import time
from pathlib import Path
from PIL import Image
import numpy as np
from training_client.client import Client


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
    c=Client(port=50051);drone=Client(port=50051,device='uav-01');air=Client(port=50052,device='uav-01')
    original=c.rpc('sim.get_state');report=dict(passed=False,models={})
    def lights():
        return next(x for x in c.rpc('sim.get_state')['devices'] if x['id']=='uav-01')['navigation_lights']
    def wait(predicate,seconds=70):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate():return
            time.sleep(.1)
        raise TimeoutError('Acceptance timeout')
    def environment(hour):
        c.rpc('environment.configure',time_override=True,hour=hour,fog=0,rain=0)
        time.sleep(.2)
    def image(name,channel):
        p=c.rpc('camera.stream_frame',channel=channel)
        (out/(name+'.jpg')).write_bytes(base64.b64decode(p['image_base64']))
    try:
        assert air.rpc('sim.get_state')['flight_status']=='ready'
        c.rpc('observer.set_mode',mode='follow');c.rpc('gimbal.set_tracking',enabled=True)
        air.rpc('flight.takeoff');wait(lambda:not air.rpc('sim.get_state')['command_active'])
        assert min(air.rpc('sim.get_state')['motor_rpm'])>1000
        for model in ('mavic3','avata','mavic3'):
            drone.rpc('drone.set_model',model=model);environment(12)
            day=lights();assert day['lamp_count']==4 and not any(day[k] for k in ('night','red_on','green_on'))
            environment(22);seen=set();states=[];end=time.monotonic()+4
            pixel_max={'red':0,'green':0};pixel_min={'red':100000,'green':100000}
            while time.monotonic()<end:
                state=lights();assert state['night'] and state['lamp_count']==4
                phase='red' if state['red_on'] else 'green' if state['green_on'] else 'off'
                assert not (state['red_on'] and state['green_on'])
                if phase not in seen:
                    image(model+'_'+phase,'CH1');image(model+'_'+phase+'_follow','OBS')
                packet=c.rpc('camera.stream_frame',channel='CH1')
                data=base64.b64decode(packet['image_base64']);rgb=np.asarray(Image.open(io.BytesIO(data))).astype(float)
                # The tracking target is central; exclude red roofs at image edges.
                h,w=rgb.shape[:2];a=rgb[int(h*.35):int(h*.65),int(w*.3):int(w*.7)]
                for color,index in [('red',0),('green',1)]:
                    count=int(((a[:,:,index]>55)&(a[:,:,index]-a[:,:,(index+1)%3]>25)&(a[:,:,index]-a[:,:,(index+2)%3]>25)).sum())
                    pixel_min[color]=min(pixel_min[color],count)
                    if count>pixel_max[color]:
                        pixel_max[color]=count;(out/(model+'_actual_'+color+'.jpg')).write_bytes(data)
                seen.add(phase);states.append(state);time.sleep(.06)
            assert seen=={'red','green','off'},seen
            assert min(pixel_max.values())>0,(model,pixel_max)
            assert all(pixel_min[k]<pixel_max[k] for k in pixel_max),(pixel_min,pixel_max)
            pair=c.sample_pair();assert all(p['objects'] for p in pair['samples'].values())
            for sensor,p in pair['samples'].items():
                (out/(model+'_'+sensor+'.jpg')).write_bytes(base64.b64decode(p['image_base64']))
            report['models'][model]=dict(day=day,night=states,pixel_max=pixel_max,pixel_min=pixel_min,pair={s:{k:v for k,v in p.items() if k!='image_base64'} for s,p in pair['samples'].items()})
        report['passed']=True
    finally:
        air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready' and max(air.rpc('sim.get_state')['motor_rpm'])<1)
        drone.rpc('drone.set_model',model=original['drone_model'])
        e=original['environment'];c.rpc('environment.configure',time_override=e['time_override'],hour=e['hour'],fog=e['fog'],rain=e['rain'],clouds=e['clouds'])
        c.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']);c.rpc('gimbal.set_tracking',enabled=original['tracking'])
        c.rpc('observer.set_mode',mode=original['observer_mode'])
        report['restored']=True;report['final_flight']=air.rpc('sim.get_state')
        (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('NAVIGATION_LIGHTS_LIVE_PASSED')


if __name__=='__main__':main()
