"""Real capture-context naming, paired atomic export and source-rate snapshot."""
import argparse
import json
from pathlib import Path
import time
from training_client.client import Client,save_pair
from training_client.storage import weather_name
from training_client.train import collect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    client=Client();direct=Client(port=50051);original=direct.rpc('sim.get_state');env=original['environment']
    report=dict(passed=False,run_id=original['run_id'],cases=[])
    def environment(**changes):
        settings={k:env[k] for k in ('time_override','hour','fog','rain','clouds')};settings.update(changes)
        direct.rpc('environment.configure',**settings)
    try:
        client.configure()
        for name,changes in [('Clear-Day',dict(time_override=True,hour=12,fog=0,rain=0,clouds=0)),
                             ('Fog-Night',dict(time_override=True,hour=22,fog=.2,rain=0,clouds=0))]:
            environment(**changes);pair=client.sample_pair()
            for packet in pair['samples'].values():
                assert packet['context_source']=='capture_tick' and packet['scenario_models']==['mavic3']
                assert weather_name(packet['environment'])==name,packet['environment']
            group=save_pair(pair,args.output/'dataset');assert group
            folder=args.output/'dataset'
            images=sorted(p for p in folder.glob('*/images/*.jpg') if group in p.name)
            assert len(images)==2 and len([p for p in folder.glob('*/labels/*.txt') if group in p.name])==2
            assert all(f'Mavic3_{name}_city_' in image.name for image in images)
            assert images[0].stem.split('_',1)[1]==images[1].stem.split('_',1)[1]
            assert not (args.output/'dataset/pairs').exists()
            report['cases'].append(dict(weather=name,sample_group_id=group,images=[p.name for p in images]))
        environment(time_override=True,hour=12,fog=0,rain=0,clouds=0)
        direct.rpc('gimbal.set_angles',yaw_deg=0,pitch_deg=25)
        negative=client.sample_pair();assert all(p['negative_sample'] for p in negative['samples'].values())
        group=save_pair(negative,args.output/'dataset')
        folder=args.output/'dataset'
        assert all(p.read_bytes()==b'' for p in folder.glob('*/labels/*.txt') if group in p.name)
        report['cases'].append(dict(weather='Clear-Day',negative_sample=True,sample_group_id=group,images=[p.name for p in sorted(folder.glob('*/images/*.jpg')) if group in p.name]))
        images,_,_=collect(args.output/'dataset','infrared');assert len(images)==3
        before=direct.rpc('sim.get_state');start=time.monotonic();time.sleep(2);after=direct.rpc('sim.get_state');duration=time.monotonic()-start
        report['source_new_frames_fps']={channel:(after['streams'][channel]['completed_frames']-before['streams'][channel]['completed_frames'])/duration for channel in ('CH1','CH2')}
        returns=[]
        for _ in range(6):
            pair=client.sample_pair();returns.append(time.monotonic());assert pair['samples']['visible']['simulation_time_s']==pair['samples']['infrared']['simulation_time_s']
        report['six_pairs_measured_fps']=5/(returns[-1]-returns[0])
        report['limits']=dict(video_poll_default=20,video_poll_max=30,gt_display_default=1,gt_save_default=1,gt_max=2)
        report['passed']=True
    finally:
        environment()
        if original['tracking']:direct.rpc('gimbal.set_tracking',enabled=True)
        else:direct.rpc('gimbal.set_angles',yaw_deg=original['yaw_deg'],pitch_deg=original['pitch_deg'])
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
