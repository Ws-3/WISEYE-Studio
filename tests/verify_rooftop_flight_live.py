"""Validate one-gimbal roof deployment and actual Mavic takeoff/landing."""
import argparse,base64,json,time,math
from pathlib import Path
from training_client.client import Client

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    c=Client(port=50051);air=Client(port=50052,device='uav-01')
    original=c.rpc('sim.get_state');sensors=original['sensors'];report=dict(passed=False,run_id=original['run_id'])
    def wait(predicate,seconds=70):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            if predicate():return
            time.sleep(.25)
        raise TimeoutError('Flight/capture acceptance timeout')
    def image(name,channel):
        packet=c.rpc('camera.stream_frame',channel=channel)
        (args.output/(name+'.jpg')).write_bytes(base64.b64decode(packet['image_base64']))
    def configure(sensor,**changes):
        values={k:sensors[sensor][k] for k in ('enabled','fov_deg')}
        if sensor=='infrared':values.update(palette=sensors[sensor]['palette'],noise=sensors[sensor]['noise'],thermal_profile=sensors[sensor]['thermal_profile'])
        return c.rpc('sensor.configure',sensor=sensor,**{**values,**changes})
    airborne=False
    try:
        inventory=original['devices'];assert len([d for d in inventory if d['kind']=='gimbal'])==1
        assert len([d for d in inventory if d['kind']=='drone'])==1
        fleet=json.loads((Path(__file__).resolve().parents[1]/'ue5/WISEYE/Config/WISEYE/Fleets/city.json').read_text(encoding='utf-8-sig'))
        expected=next(d['position_cm'] for d in fleet['devices'] if d['id']=='ptz-01')
        assert math.dist(original['gimbal_position_cm'],expected)<.1
        assert air.rpc('sim.get_state')['flight_status']=='ready'
        drone_spawn=next(d['position_cm'] for d in fleet['devices'] if d['id']=='uav-01')
        assert abs(original['drone_position_cm'][2]-drone_spawn[2])<35
        c.rpc('observer.set_mode',mode='overview');time.sleep(.5);image('roof_overview','OBS')
        configure('infrared',thermal_profile='facade',fov_deg=15);configure('visible',fov_deg=15)
        c.rpc('gimbal.set_tracking',enabled=True);time.sleep(.7)
        before=c.rpc('sim.get_state');start_z=before['drone_position_cm'][2]
        report['initial']=before;image('landed_visible','CH1');image('landed_infrared','CH2')
        air.rpc('flight.takeoff');airborne=True
        wait(lambda:c.rpc('sim.get_state')['drone_position_cm'][2]>start_z+100)
        wait(lambda:not air.rpc('sim.get_state')['command_active'])
        time.sleep(1);hover=c.rpc('sim.get_state');report['hover']=hover
        assert min(hover['motor_rpm'])>1000
        assert hover['sensors']['infrared']['target_pixels']>0
        pair=c.sample_pair();report['hover_pair']={sensor:{k:v for k,v in packet.items() if k!='image_base64'} for sensor,packet in pair['samples'].items()}
        assert all(packet['objects'] for packet in pair['samples'].values()),'Flying target must have separate GT in both cameras'
        image('hover_visible','CH1');image('hover_infrared','CH2');image('hover_overview','OBS')
        air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready' and max(air.rpc('sim.get_state')['motor_rpm'])<1);airborne=False
        wait(lambda:max(c.rpc('sim.get_state')['motor_rpm'])<1)
        landed=c.rpc('sim.get_state');report['landed']=landed
        assert abs(landed['drone_position_cm'][2]-start_z)<30,'Drone did not land back on the roof'
        assert math.dist(landed['drone_position_cm'][:2],before['drone_position_cm'][:2])<100
        report['passed']=True
    finally:
        if airborne:
            air.rpc('flight.land');wait(lambda:air.rpc('sim.get_state')['flight_status']=='ready' and max(air.rpc('sim.get_state')['motor_rpm'])<1)
        for sensor in ('visible','infrared'):configure(sensor)
        c.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg']);c.rpc('gimbal.set_tracking',enabled=original['tracking'])
        c.rpc('observer.set_mode',mode=original['observer_mode'])
        report['restored']=True
        (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('ROOFTOP_FLIGHT_PASSED',flush=True)

if __name__=='__main__':main()
