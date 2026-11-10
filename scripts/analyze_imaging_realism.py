"""Fixed-view imaging A/B evidence, without calling pixel differences realism scores."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scripts.infrared_baseline import pixels_summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    reports=[json.loads((p/'report.json').read_text(encoding='utf-8')) for p in [args.before,args.after]]
    assert all(r.get('passed') and r.get('landed') and r.get('owned_session_stopped') for r in reports)
    report={'before_run':reports[0]['run_id'],'after_run':reports[1]['run_id'],'measurements':{},
        'limitations':['Independent runs; moving traffic and temporal AA are not pixel-registered.',
            'Road ROI is one manually selected 60x60 paved patch at x=330:390,y=120:180.',
            '8-bit display-domain measurements, not temperature calibration or a realism percentage.',
            'Optical realism remains uncalibrated without a matched real camera and exposure metadata.']}
    for name in reports[0]['captures']:
        row={}
        for stage,folder in [('before',args.before),('after',args.after)]:
            im=Image.open(folder/(name+'.jpg'));a=np.asarray(im.convert('L'))
            expected=(640,512) if name.endswith('-ir') else (1920,1080)
            assert im.size==expected,(name,im.size)
            row[stage]={'frame':pixels_summary(a)}
            if name.endswith('aerial-ir'):
                row[stage]['road']=pixels_summary(a[120:180,330:390])
        poses=[r['captures'][name] for r in reports]
        if all('camera_position_cm' in p for p in poses):
            row['camera_position_delta_cm']=math.dist(*(p['camera_position_cm'] for p in poses))
            rotations=[p['camera_rotation_pitch_yaw_roll_deg'] for p in poses]
            row['max_camera_rotation_delta_deg']=max(abs((a-b+180)%360-180) for a,b in zip(*rotations))
        report['measurements'][name]=row
    report['temporal_road_roi']=reports[1].get('temporal_road_roi',{})
    report['temporal_median_range_dn']={name:max(r['median_dn'] for r in rows)-min(r['median_dn'] for r in rows)
        for name,rows in report['temporal_road_roi'].items()}
    (args.output/'measurements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 双光成像改进实测', '', '| 同一图像路面选区 | 修改前灰度中位数 | 修改后 | 修改前标准差 | 修改后 |',
        '|---|---:|---:|---:|---:|']
    for name,row in report['measurements'].items():
        if 'road' in row['before']:
            b,a=row['before']['road'],row['after']['road']
            lines.append(f"| {name} | {b['p50']:.1f} | {a['p50']:.1f} | {b['std']:.2f} | {a['std']:.2f} |")
    lines += ['', '完整姿态误差、全图亮暗端比例及时序选区统计见 measurements.json。不同独立会话不计算PSNR/SSIM。', '',
        '软件对比图保持原始灰度，不分别自动拉伸。真实度不是用前后像素差定义的。']
    (args.output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for sensor in ['ir','visible']:
        fig,axes=plt.subplots(2,2,figsize=(11,7.5))
        for i,period in enumerate(['day','night']):
            for j,(label,folder) in enumerate([('BEFORE',args.before),('AFTER',args.after)]):
                name=period+'-aerial-'+sensor
                im=Image.open(folder/(name+'.jpg'))
                axes[i,j].imshow(im);axes[i,j].axis('off')
                axes[i,j].set_title(f'{period.upper()} / {label}',fontsize=11)
                if sensor=='ir':
                    axes[i,j].plot([330,390,390,330,330],[120,120,180,180,120],color='lime',lw=.8)
        fig.suptitle('WISEYE aerial '+sensor.upper()+' / original display levels',fontsize=13)
        fig.tight_layout();fig.savefig(args.output/f'aerial-{sensor}-comparison.png',dpi=135);plt.close(fig)
    fig,axes=plt.subplots(4,2,figsize=(11,13))
    for i,(period,sensor) in enumerate([('day','visible'),('day','ir'),('night','visible'),('night','ir')]):
        for j,(label,folder) in enumerate([('BEFORE',args.before),('AFTER',args.after)]):
            axes[i,j].imshow(Image.open(folder/(period+'-gimbal-'+sensor+'.jpg')));axes[i,j].axis('off')
            axes[i,j].set_title(f'{period} {sensor} / {label}',fontsize=9)
    fig.tight_layout();fig.savefig(args.output/'gimbal-comparison.png',dpi=120);plt.close(fig)
    print('\n'.join(lines))


if __name__=='__main__':main()
