"""Real dual-camera geometry and independent acquisition; restores runtime settings."""
import argparse,json,math,time
from pathlib import Path
import apps.desktop_app.main
from training_client.client import Client,RPCError,validate_pair
from training_client.fusion import decode,blend_pair

FIELDS=('mount_x_cm','mount_y_cm','mount_z_cm','boresight_pitch_deg','boresight_yaw_deg','boresight_roll_deg')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--device',default='ptz-01')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    c=Client(port=50051,device=args.device);s=c.rpc('sim.get_state');original=s['sensors']
    report=dict(passed=False,run_id=s['run_id'],checks={},poses=[],pairs=[])
    def configure(sensor,**changes):
        values={k:original[sensor][k] for k in ('enabled','fov_deg',*FIELDS)}
        if sensor=='infrared':values.update(palette=original[sensor]['palette'],noise=original[sensor]['noise'])
        return c.rpc('sensor.configure',sensor=sensor,**{**values,**changes})
    def sensor_state():return c.rpc('sim.get_state')['sensors']
    def same(a,b):return max(abs(x-y) for x,y in zip(a,b))<.001
    try:
        configure('visible',enabled=True);configure('infrared',enabled=True)
        for yaw,pitch in [(0,0),(60,20),(-70,-10)]:
            c.rpc('gimbal.set_angles',yaw_deg=yaw,pitch_deg=pitch);time.sleep(.2)
            ss=sensor_state();v,i=ss['visible'],ss['infrared']
            baseline=math.dist(v['camera_position_cm'],i['camera_position_cm'])
            assert abs(baseline-math.dist([v[k] for k in FIELDS[:3]],[i[k] for k in FIELDS[:3]]))<.001
            assert baseline>1
            assert not same(v['camera_rotation_pitch_yaw_roll_deg'],i['camera_rotation_pitch_yaw_roll_deg'])
            report['poses'].append(dict(yaw=yaw,pitch=pitch,baseline_cm=baseline,visible=v,infrared=i))
        c.rpc('gimbal.set_tracking',enabled=True);time.sleep(1)
        pair=c.sample_pair();validate_pair(pair,args.device)
        assert math.dist(pair['samples']['visible']['camera_position_cm'],pair['samples']['infrared']['camera_position_cm'])>1
        for sensor,packet in pair['samples'].items():
            decode(packet).save(str(args.output/(sensor+'.png')))
            report['pairs'].append({k:v for k,v in packet.items() if k!='image_base64'})
        try:blend_pair(pair,mode='strict');raise AssertionError('An unregistered stereo pair was silently fused in strict mode')
        except ValueError:report['checks']['unaligned_fusion_refused']=True
        c.rpc('gimbal.set_angles',yaw_deg=0,pitch_deg=0);time.sleep(.2)
        before=sensor_state();configure('infrared',mount_y_cm=original['infrared']['mount_y_cm']+2,boresight_yaw_deg=1.2)
        after=sensor_state()
        assert same(before['visible']['camera_position_cm'],after['visible']['camera_position_cm'])
        assert abs(math.dist(before['infrared']['camera_position_cm'],after['infrared']['camera_position_cm'])-2)<.001
        assert after['infrared']['boresight_yaw_deg']==1.2
        for changes in [dict(mount_x_cm=101),dict(boresight_yaw_deg=16),dict(mount_y_cm=True),dict(boresight_pitch_deg='bad')]:
            old=sensor_state()['infrared']
            try:configure('infrared',**changes);raise AssertionError('Invalid calibration accepted')
            except RPCError:pass
            new=sensor_state()['infrared'];assert all(old[k]==new[k] for k in FIELDS)
        for off,on in [('visible','infrared'),('infrared','visible')]:
            c.rpc('sensor.set_enabled',sensor=off,enabled=False);time.sleep(.4)
            a=sensor_state();time.sleep(.4);b=sensor_state()
            assert a[off]['capture_sequence']==b[off]['capture_sequence']
            assert b[on]['capture_sequence']>a[on]['capture_sequence']
            try:c.sample_pair();raise AssertionError('Disabled sensor yielded a pair')
            except RPCError as e:assert e.code=='sensor_disabled'
            c.rpc('sensor.set_enabled',sensor=off,enabled=True)
        report['checks'].update(rotation_preserves_physical_baseline=True,independent_calibration=True,invalid_atomic=4,independent_power=True,same_tick_pair=True)
        report['passed']=True
    finally:
        for sensor in ('visible','infrared'):configure(sensor)
        c.rpc('gimbal.set_angles',yaw_deg=s['yaw_deg'],pitch_deg=s['pitch_deg'])
        c.rpc('gimbal.set_tracking',enabled=s['tracking'])
        report['restored']=True
        (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('DUAL_CAMERA_ACCEPTANCE_PASSED',flush=True)

if __name__=='__main__':main()
