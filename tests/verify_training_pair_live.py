"""Paired capture through the simulator-owned service, without a gateway launcher."""
import argparse
import json
from pathlib import Path
import time
from training_client.client import Client, RPCError, save_pair, validate_pair
from training_client.preview import QApplication, render_packet, draw_gt
from training_client.fusion import blend_pair


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--device',default='ptz-01')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    app=QApplication([]);client=Client(device=args.device);direct=Client(port=50051,device=args.device)
    original=direct.rpc('sim.get_state')
    assert original['paired_training_samples_supported']
    report=dict(passed=False,run_id=original['run_id'],pairs=[],checks={})
    def configure(sensor,fov):
        old=original['sensors'][sensor];values=dict(sensor=sensor,enabled=old['enabled'],fov_deg=fov)
        if sensor=='infrared':values.update(palette=old['palette'],noise=old['noise'])
        direct.rpc('sensor.configure',**values)
    def capture(name):
        time.sleep(.6);pair=client.sample_pair();validate_pair(pair,args.device)
        assert pair['run_id']==original['run_id']
        for sensor,packet in pair['samples'].items():
            assert packet['simulation_time_s']==pair['simulation_time_s']
            render_packet(packet).save(str(args.output/f'{name}_{sensor}.png'))
        try:draw_gt(blend_pair(pair,.5),pair['samples']['infrared']).save(str(args.output/f'{name}_fusion.png'))
        except ValueError as error:
            assert '双相机' in str(error),str(error)
            report['checks']['fusion_requires_stereo_registration']=True
        save_pair(pair,args.output/'dataset')
        report['pairs'].append({k:v for k,v in pair.items() if k!='samples'} | dict(samples={s:{k:v for k,v in p.items() if k!='image_base64'} for s,p in pair['samples'].items()}))
        return pair
    try:
        client.configure();direct.rpc('gimbal.set_tracking',enabled=True)
        configure('visible',5);configure('infrared',5);time.sleep(2)
        first=capture('target')
        assert first['samples']['infrared']['objects'] and first['samples']['visible']['objects']
        # Different FOVs require optical resampling, not direct image stretching.
        configure('visible',10);capture('different_fov')
        # Double-disabled state is an explicit error, never an old pair.
        direct.rpc('sensor.set_enabled',sensor='infrared',enabled=False)
        try:client.sample_pair();raise AssertionError('Disabled sensor produced a pair')
        except RPCError as error:assert error.code=='sensor_disabled'
        direct.rpc('sensor.set_enabled',sensor='infrared',enabled=True)
        configure('visible',5)
        resumed=capture('resumed')
        assert resumed['pair_id']!=first['pair_id']
        direct.rpc('gimbal.set_angles',yaw_deg=0,pitch_deg=25);time.sleep(.5)
        empty=capture('negative')
        assert all(p['negative_sample'] for p in empty['samples'].values())
        # Single-source reception continues to work on the same endpoint.
        time.sleep(.6);client.sensor='visible';single=client.sample()
        assert single['sensor_id']=='visible'
        report['checks'].update(same_tick=True,different_fov=True,disabled_rejected=True,
                              resumed_fresh=True,paired_negatives=True,single_source=True)
        report['passed']=True
    finally:
        for sensor in ('visible','infrared'):configure(sensor,original['sensors'][sensor]['fov_deg'])
        client.configure()
        if original['tracking']:direct.rpc('gimbal.set_tracking',enabled=True)
        else:direct.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg'])
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('Live paired VIS/IR, registration, negatives, disabled/resume and single-source checks passed',flush=True)


if __name__=='__main__':main()
