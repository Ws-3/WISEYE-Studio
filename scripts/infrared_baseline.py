"""Unpaired, display-domain IR reference measurements; never a radiometric score."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def pixels_summary(values):
    v = np.asarray(values, dtype=np.float64).ravel()
    if not v.size:
        return None
    hist = np.bincount(v.astype(np.uint8), minlength=256).astype(float)
    hist /= hist.sum()
    nonzero = hist[hist > 0]
    return dict(pixels=int(v.size), mean=float(v.mean()), std=float(v.std()),
        **{f'p{q:02}': float(np.percentile(v, q)) for q in [1, 5, 50, 95, 99]},
        bright_ge204=float(np.mean(v >= 204)), nearwhite_ge245=float(np.mean(v >= 245)),
        clipped_ge254=float(np.mean(v >= 254)), black_le1=float(np.mean(v <= 1)),
        entropy_bits=float(-np.sum(nonzero*np.log2(nonzero))), histogram=hist.tolist())


def normalized_box(box, shape, padding=0):
    h, w = shape
    x, y, bw, bh = box
    coords = np.asarray(box, dtype=float)
    if not np.isfinite(coords).all() or bw <= 0 or bh <= 0 or bw > 1 or bh > 1 or not (0 <= x <= 1 and 0 <= y <= 1):
        raise ValueError('Invalid normalized box')
    return (max(0, int(np.floor((x-bw/2)*w))-padding),
            max(0, int(np.floor((y-bh/2)*h))-padding),
            min(w, int(np.ceil((x+bw/2)*w))+padding),
            min(h, int(np.ceil((y+bh/2)*h))+padding))


def box_mask(shape, boxes, padding=0):
    mask = np.zeros(shape, dtype=bool)
    for b in boxes:
        x1, y1, x2, y2 = normalized_box(b['xywh_normalized'], shape, padding)
        mask[y1:y2, x1:x2] = True
    return mask


def polygon_mask(shape, polygon):
    coords = np.asarray(polygon, dtype=float)
    if coords.ndim != 2 or coords.shape[0] < 3 or coords.shape[1] != 2 or not np.isfinite(coords).all() or np.any(coords < 0) or np.any(coords > 1):
        raise ValueError('ROI needs >=3 normalized vertices')
    h, w = shape
    image = Image.new('1', (w, h))
    ImageDraw.Draw(image).polygon([(round(x*(w-1)), round(y*(h-1))) for x, y in coords], fill=1)
    return np.asarray(image, dtype=bool)


def target_proxies(gray, boxes, valid):
    occupied = box_mask(gray.shape, boxes, padding=2)
    results = []
    for b in boxes:
        x1, y1, x2, y2 = normalized_box(b['xywh_normalized'], gray.shape)
        target = np.zeros(gray.shape, bool)
        target[y1:y2, x1:x2] = True
        pad = max(4, (max(x2-x1, y2-y1)+1)//2)
        outer = np.zeros(gray.shape, bool)
        h, w = gray.shape
        outer[max(0,y1-pad):min(h,y2+pad), max(0,x1-pad):min(w,x2+pad)] = True
        foreground = gray[target & valid]
        background = gray[outer & ~occupied & valid]
        result = dict(class_id=b['class_id'], box_width_px=x2-x1, box_height_px=y2-y1,
            foreground_pixels=int(foreground.size), background_pixels=int(background.size),
            signed_contrast_dn=None, cnr_proxy=None)
        if foreground.size and background.size >= 16:
            delta = float(np.mean(foreground)-np.mean(background))
            result['signed_contrast_dn'] = delta
            # Full bbox, not segmented target. Background texture is not sensor noise.
            std = float(np.std(background))
            result['cnr_proxy'] = abs(delta)/std if std > 1e-6 else None
        results.append(result)
    return results


def cropped_boxes(entry, shape):
    boxes=entry.get('boxes', [])
    border=entry.get('crop_border_px',0)
    if not border:
        return boxes
    space=entry.get('boxes_coordinate_space')
    if space not in ['raw','cropped']:
        raise ValueError('Border crop requires explicit boxes_coordinate_space: raw or cropped')
    if space=='cropped':
        return boxes
    h,w=shape
    raw_h,raw_w=h+2*border,w+2*border
    result=[]
    for b in boxes:
        x1,y1,x2,y2=normalized_box(b['xywh_normalized'],(raw_h,raw_w))
        x1,x2=np.clip([x1-border,x2-border],0,w)
        y1,y2=np.clip([y1-border,y2-border],0,h)
        if x2>x1 and y2>y1:
            result.append({**b,'xywh_normalized':[(x1+x2)/(2*w),(y1+y2)/(2*h),(x2-x1)/w,(y2-y1)/h]})
    return result


def load_frame(entry, root):
    path = Path(entry['path'])
    if not path.is_absolute():
        path = root/path
    payload = path.read_bytes()
    sha = hashlib.sha256(payload).hexdigest()
    if entry.get('sha256') and sha != entry['sha256']:
        raise ValueError(f'Image changed: {path}')
    with Image.open(path) as image:
        rgb = image.convert('RGB')
    crop = entry.get('crop_border_px', 0)
    if crop:
        if rgb.width <= 2*crop or rgb.height <= 2*crop:
            raise ValueError('Border crop removes image')
        rgb = rgb.crop((crop,crop,rgb.width-crop,rgb.height-crop))
    gray = np.asarray(rgb.convert('L'), dtype=np.float64)
    # Keep display polarity. Black-hot is a separate comparison stratum.
    valid = np.ones(gray.shape, bool)
    for polygon in entry.get('exclude_polygons', []):
        valid &= ~polygon_mask(gray.shape, polygon)
    return path, sha, rgb, gray, valid


def measure(entry, root):
    path, sha, rgb, gray, valid = load_frame(entry, root)
    boxes = cropped_boxes(entry,gray.shape)
    result = {k: v for k, v in entry.items() if k not in ['boxes','road_polygons','exclude_polygons']}
    result.update(path=str(path), sha256=sha, width=rgb.width, height=rgb.height,
        boxes_before_crop=len(entry.get('boxes',[])), boxes_measured=len(boxes),
        frame=pixels_summary(gray[valid]), targets=target_proxies(gray, boxes, valid))
    road = np.zeros(gray.shape, bool)
    for polygon in entry.get('road_polygons', []):
        road |= polygon_mask(gray.shape, polygon)
    road &= valid & ~box_mask(gray.shape, boxes, padding=3)
    result['road'] = pixels_summary(gray[road])
    result['road_annotation'] = 'manual_polygon_excluding_labeled_targets_3px' if road.any() else 'unavailable'
    return result


def distribution_gap(a, b):
    # Wasserstein-1 for equally spaced discrete display intensities, unit DN.
    return float(np.sum(np.abs(np.cumsum(a)-np.cumsum(b))))


def make_report(manifest, output, root):
    output.mkdir(parents=True, exist_ok=True)
    entries = manifest['entries']
    if len({e['id'] for e in entries}) != len(entries):
        raise ValueError('Duplicate frame IDs')
    results = [measure(e, root) for e in entries]
    groups = {}
    for r in results:
        key = '/'.join(r.get(k, 'unknown') for k in ['view','domain','dataset','condition','polarity'])
        groups.setdefault(key, []).append(r)
    aggregates = {}
    for key, records in groups.items():
        aggregate = {'frames':len(records), 'sequence_or_stratum_groups':len({r['group'] for r in records})}
        for scope in ['frame', 'road']:
            stats = [r[scope] for r in records if r[scope] is not None]
            if not stats:
                continue
            aggregate[scope] = {'roi_frames':len(stats), **{name:float(np.median([s[name] for s in stats]))
                for name in ['p50','std','bright_ge204','nearwhite_ge245','clipped_ge254']},
                'equal_frame_histogram':np.mean([s['histogram'] for s in stats], axis=0).tolist()}
        aggregates[key] = aggregate
        target_records=[t for r in records for t in r['targets'] if t['signed_contrast_dn'] is not None]
        aggregate['target_proxy']={'valid_boxes':len(target_records)}
        if target_records:
            aggregate['target_proxy'].update({k:float(np.median([t[k] for t in target_records if t[k] is not None]))
                for k in ['box_width_px','box_height_px','signed_contrast_dn']})
        aggregate['targets_by_class']={}
        for cls in sorted({t['class_id'] for t in target_records}):
            subset=[t for t in target_records if t['class_id']==cls]
            aggregate['targets_by_class'][str(cls)]={'valid_boxes':len(subset),
                **{k:float(np.median([t[k] for t in subset])) for k in ['box_width_px','box_height_px','signed_contrast_dn']}}
    comparisons = []
    for sim in results:
        if sim['domain'] != 'sim' or not sim.get('road'):
            continue
        for real in results:
            if real['domain'] != 'real' or not real.get('road'):
                continue
            # No global pairing and no comparisons across view, condition or polarity.
            if any(sim.get(k) != real.get(k) for k in ['view','condition','polarity']):
                continue
            comparisons.append({'sim':sim['id'], 'real':real['id'],
                'kind':'unpaired_road_display_distribution_only',
                'wasserstein1_dn':distribution_gap(sim['road']['histogram'], real['road']['histogram']),
                'median_delta_dn':sim['road']['p50']-real['road']['p50']})
    report = dict(schema=1, limitations=manifest.get('limitations', []), measurements=results,
        aggregates=aggregates, road_comparisons=comparisons)
    (output/'measurements.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    with (output/'frames.csv').open('w', encoding='utf-8-sig', newline='') as f:
        columns=['id','domain','view','dataset','condition','width','height','road_p50','road_bright_ge204','frame_p50','frame_bright_ge204']
        writer=csv.DictWriter(f, fieldnames=columns); writer.writeheader()
        for r in results:
            row={k:r[k] for k in columns[:7]}
            row.update(width=r['width'], height=r['height'])
            for scope in ['road','frame']:
                for metric in ['p50','bright_ge204']:
                    row[scope+'_'+metric]=(r[scope] or {}).get(metric)
            writer.writerow(row)
    lines=['# 红外真实／仿真对照基准（初版）', '',
        '只衡量解码后的 8 位显示图像；不是温度误差、物理 SNR 或检测精度。真实与仿真不是同一地点，不计算 SSIM/PSNR。', '',
        '| 视角/来源/条件/极性 | 帧数 | 全图灰度中位数 | 亮像素≥204 | 路面ROI帧数 | 路面灰度中位数 | 路面标准差 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for key, a in aggregates.items():
        road=a.get('road', {})
        median=f"{road['p50']:.1f}" if road else '—'
        std=f"{road['std']:.2f}" if road else '—'
        lines.append(f"| {key} | {a['frames']} | {a['frame']['p50']:.1f} | {a['frame']['bright_ge204']:.1%} | {road.get('roi_frames',0)} | {median} | {std} |")
    lines += ['', '## 真实目标对比代理（整框，来源类别编号各自独立）', '',
        '| 分组 | 有效框 | 宽×高中位数 / px | 框内−环带灰度中位差 / DN |', '|---|---:|---:|---:|']
    for key,a in aggregates.items():
        for cls,t in a['targets_by_class'].items():
            lines.append(f"| {key}/class-{cls} | {t['valid_boxes']} | {t['box_width_px']:.1f}×{t['box_height_px']:.1f} | {t['signed_contrast_dn']:.1f} |")
    lines += ['', '分组统计先按每帧计算，再取帧间中位数；不同分辨率不以像素数量加权。文件名中的 HIT 飞行参数是采集分层，不是已证明独立的视频序列。', '',
        '## 限制', ''] + ['- '+s for s in manifest.get('limitations', [])]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    render_figures(entries, report, output, root)
    print(f'{len(results)} measured frames, {len(comparisons)} unpaired road comparisons -> {output}')
    return report


def render_figures(entries, report, output, root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    # All real references stay local; do not redistribute local/unknown-license photos.
    for view in ['aerial','gimbal']:
        chosen=[e for e in entries if e['view']==view]
        fig, axes=plt.subplots((len(chosen)+3)//4, 4, figsize=(14, 2.8*((len(chosen)+3)//4)), squeeze=False)
        for ax in axes.flat:
            ax.axis('off')
        for ax,e in zip(axes.flat, chosen):
            _,_,rgb,_,_=load_frame(e,root); ax.imshow(rgb)
            for polygon in e.get('road_polygons',[]):
                p=np.asarray(polygon+[polygon[0]])*[rgb.width-1,rgb.height-1]
                ax.plot(p[:,0],p[:,1],color='lime',lw=1)
            if view=='gimbal':
                for b in cropped_boxes(e,(rgb.height,rgb.width)):
                    x1,y1,x2,y2=normalized_box(b['xywh_normalized'],(rgb.height,rgb.width))
                    ax.plot([x1,x2,x2,x1,x1],[y1,y1,y2,y2,y1],color='lime',lw=.7)
            ax.set_title(f"{e['domain']} {e['dataset']} {e['condition']}\n{e['id'][:42]}",fontsize=7)
        fig.tight_layout(); fig.savefig(output/f'{view}-contact-sheet.jpg',dpi=110); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4))
    for key,a in report['aggregates'].items():
        if 'road' in a:
            ax.plot(a['road']['equal_frame_histogram'],label=key,linewidth=1)
    ax.set(xlabel='Decoded display intensity (DN)',ylabel='Fraction / intensity bin',title='Manual road ROIs: unpaired pilot, different scenes')
    ax.legend(fontsize=6);fig.tight_layout();fig.savefig(output/'road-distributions.png',dpi=160);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--references',type=Path,help='Optional downloaded/local reference manifest')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    if args.references:
        manifest['entries']=json.loads(args.references.read_text(encoding='utf-8'))['entries']+manifest['entries']
    for entry in manifest['entries']:
        roi=manifest.get('road_rois',{}).get(entry['id'])
        if roi:
            entry['road_polygons']=roi
    make_report(manifest,args.output,args.root)


if __name__=='__main__':
    main()
