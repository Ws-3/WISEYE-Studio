"""Read-only local sampling and bounded official HIT-UAV downloads. No dataset moves."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'builds/research-data'
REPO = 'suojiashun/HIT-UAV-Infrared-Thermal-Dataset'
HIT_TREE = '669259659b21a2737ca9f5e4bc81892acbe6ecd8'


def fetch(url, dest):
    if dest.exists() and dest.stat().st_size:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'WISEYE-reference-benchmark'}), timeout=45) as r:
                content = r.read()
            tmp = dest.with_suffix(dest.suffix + '.part')
            tmp.write_bytes(content)
            tmp.replace(dest)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def yolo_boxes(path):
    rows = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f'Expected axis-aligned YOLO box: {path}')
        cls, x, y, w, h = map(float, fields)
        if not (cls.is_integer() and cls >= 0 and 0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            raise ValueError(f'Invalid YOLO box: {path}')
        rows.append({'class_id': int(cls), 'xywh_normalized': [x, y, w, h]})
    return rows


def hit_subset(per_condition):
    tree_file = DATA / 'sources/HIT-UAV-tree.json'
    fetch(f'https://api.github.com/repos/{REPO}/git/trees/{HIT_TREE}?recursive=1', tree_file)
    tree = json.loads(tree_file.read_text(encoding='utf-8'))
    if tree['sha'] != HIT_TREE or tree.get('truncated'):
        raise ValueError('Expected complete pinned HIT-UAV tree; check cached source metadata')
    # The recursive tree SHA pins a Git tree, not a commit; raw accepts this object ID.
    revision = tree['sha']
    base = f'https://raw.githubusercontent.com/{REPO}/{revision}/'
    entries = []
    tasks = []
    paths = {r['path'] for r in tree['tree']}
    blobs = {r['path']:r.get('sha') for r in tree['tree'] if r['type']=='blob'}
    for condition, prefix in [('day', '0_'), ('night', '1_')]:
        groups = {}
        for p in sorted(paths):
            if p.startswith('normal_json/train/' + prefix) and p.endswith('.jpg'):
                group = '_'.join(Path(p).stem.split('_')[:4])
                groups.setdefault(group, []).append(p)
        # Round robin across altitude/perspective/time strata; fixed SHA order.
        selected = []
        ordered = sorted(groups, key=lambda g: hashlib.sha256(g.encode()).hexdigest())
        for g in ordered:
            groups[g].sort(key=lambda p: hashlib.sha256(p.encode()).hexdigest())
        while len(selected) < per_condition and any(groups.values()):
            for g in ordered:
                if groups[g] and len(selected) < per_condition:
                    selected.append(groups[g].pop())
        for p in selected:
            name = Path(p).name
            image_path = DATA / 'HIT-UAV/images' / name
            label_source = 'yolo_labels/train/' + Path(name).with_suffix('.txt').name
            if label_source not in paths:
                raise ValueError(f'Missing official label for {p}')
            label_path = DATA / 'HIT-UAV/labels' / Path(label_source).name
            tasks.extend([(base + p, image_path), (base + label_source, label_path)])
            parts = Path(name).stem.split('_')
            entries.append(dict(id='HIT-' + Path(name).stem, domain='real', view='aerial',
                dataset='HIT-UAV', condition=condition, polarity='white_hot',
                polarity_basis='visual review of sampled frames; verify per scene before calibration',
                altitude_m=int(parts[1]), perspective_deg=int(parts[2]),
                group='_'.join(parts[:4]), split='official_train_reference_only',
                path=str(image_path), label_path=str(label_path), source_url=base+p,
                source_revision=revision, annotation_status='official_yolo'))
    tasks.append((base + 'LICENSE', DATA / 'sources/HIT-UAV-LICENSE'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda pair: fetch(*pair), tasks))
    for url,path in tasks:
        content=path.read_bytes()
        git_blob=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if git_blob != blobs[url.removeprefix(base)]:
            raise ValueError(f'Download/cache differs from pinned official Git blob: {path}')
    for e in entries:
        e['sha256'] = digest(Path(e['path']))
        e['label_sha256'] = digest(Path(e['label_path']))
        e['boxes'] = yolo_boxes(Path(e['label_path']))
    return entries


def local_subset(root, per_dataset):
    entries = []
    for ds in ['Halmstad', 'CESE']:
        folder = root / 'infrared' / ds
        groups = {}
        for p in sorted((folder / 'images/train').glob('*.jpg')):
            if ds == 'Halmstad' and 'drone' not in p.stem.lower():
                continue
            group = re.sub(r'_f\d+$', '', p.stem) if ds == 'Halmstad' else p.stem.rsplit('_', 4)[0]
            groups.setdefault(group, []).append(p)
        chosen = sorted(groups, key=lambda g: hashlib.sha256(g.encode()).hexdigest())[:per_dataset]
        for group in chosen:
            files = groups[group]
            p = files[len(files)//2]
            label = folder / 'labels/train' / p.with_suffix('.txt').name
            if not label.exists():
                continue
            boxes = yolo_boxes(label)
            entries.append(dict(id=ds+'-'+p.stem, domain='real', view='gimbal', dataset=ds,
                condition='day_user_report', polarity='white_hot',
                polarity_basis='sample visual review; no radiometric metadata',
                group=group, split='local_train_reference_only', path=str(p),
                label_path=str(label), sha256=digest(p), label_sha256=digest(label),
                boxes=boxes, annotation_status='local_yolo_unverified_conversion',
                source_url=str(folder/'dataset_stats.json')))
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-root', type=Path)
    parser.add_argument('--per-condition', type=int, default=16)
    parser.add_argument('--per-local-dataset', type=int, default=16)
    parser.add_argument('--skip-hit', action='store_true')
    args = parser.parse_args()
    entries = [] if args.skip_hit else hit_subset(args.per_condition)
    if args.local_root:
        entries += local_subset(args.local_root, args.per_local_dataset)
    dest = DATA / 'reference_manifest.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({'schema': 1, 'purpose': 'display-domain unpaired pilot, not algorithm test split',
        'entries': entries}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(entries)} reference frames -> {dest}')


if __name__ == '__main__':
    main()
